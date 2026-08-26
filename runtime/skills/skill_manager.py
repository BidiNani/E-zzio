import ast
import sys
import importlib
import importlib.util
from pathlib import Path
from datetime import datetime
import shutil
import os
import subprocess


class SkillSecurityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.violations = []
        self.forbidden_modules = {"subprocess", "ctypes", "multiprocessing", "dotenv", "shutil", "glob"}
        self.forbidden_attributes = {"environ", "getenv", "putenv", "system", "popen", "eval", "exec", "read_text", "read_bytes"}
        self.tainted_vars = set()
        self.blocked_aliases = set()

    def visit_Import(self, node):
        for alias in node.names:
            base_module = alias.name.split(".")[0]
            if base_module in self.forbidden_modules or base_module == "pathlib":
                self.blocked_aliases.add(alias.asname or alias.name)
                if base_module in self.forbidden_modules:
                    self.violations.append(f"Module interdit importé : {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            base_module = node.module.split(".")[0]
            if base_module in self.forbidden_modules or base_module == "pathlib":
                for alias in node.names:
                    self.blocked_aliases.add(alias.asname or alias.name)

            if base_module in self.forbidden_modules:
                self.violations.append(f"Module interdit importé depuis : {node.module}")

            if node.module == "runtime.security.secrets" or node.module.endswith("secrets"):
                for alias in node.names:
                    if alias.name == "SecretKeyManager":
                        self.violations.append("Import interdit : Accès au Kernel HMAC refusé.")

        for alias in node.names:
            if alias.name in self.forbidden_attributes:
                self.violations.append(f"Import direct d'un attribut interdit : {alias.name}")
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr in self.forbidden_attributes:
            self.violations.append(f"Accès à un attribut système ou I/O sensible détecté : {node.attr}")
        self.generic_visit(node)

    def visit_Assign(self, node):
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            val = node.value.value
            if "secrets" in val or ".env" in val or ".." in val:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.tainted_vars.add(target.id)
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id in self.blocked_aliases:
                    self.violations.append(f"Appel I/O interdit via alias bloqué : {node.func.value.id}.{node.func.attr}()")

        if isinstance(node.func, ast.Name):
            # BLOCAGE DE LA RÉFLEXION DYNAMIQUE AJOUTÉ
            if node.func.id in {"eval", "exec", "globals", "locals", "getattr", "__import__", "compile"}:
                self.violations.append(f"Fonction globale critique interdite : {node.func.id}()")

            elif node.func.id in {"open", "Path"}:
                if getattr(node, "args", None):
                    first_arg = node.args[0]
                    if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                        if "secrets" in first_arg.value or ".env" in first_arg.value or ".." in first_arg.value:
                            self.violations.append(f"Appel I/O interdit ({node.func.id}) vers cible critique : {first_arg.value}")
                    elif isinstance(first_arg, ast.Name):
                        if first_arg.id in self.tainted_vars:
                            self.violations.append(f"Appel I/O interdit ({node.func.id}) via variable compromise : {first_arg.id}")

        self.generic_visit(node)


class EzzioSkillManager:
    def __init__(self, base_path="runtime/skills"):
        self.base_path = Path(base_path)
        self.staging_dir = self.base_path / "staging"
        self.active_dir = self.base_path / "active"
        self.archive_dir = self.base_path / "archive"
        self.loaded_skills = {}

        if str(self.active_dir.resolve()) not in sys.path:
            sys.path.insert(0, str(self.active_dir.resolve()))

    def validate_skill(self, file_path: Path) -> tuple[bool, list[str]]:
        try:
            source_code = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source_code, filename=str(file_path))
            visitor = SkillSecurityVisitor()
            visitor.visit(tree)
            if visitor.violations:
                return False, visitor.violations
            return True, []
        except Exception as e:
            return False, [f"Erreur de syntaxe ou d'analyse : {str(e)}"]

    def promote_and_load(self, skill_filename: str) -> dict:
        staging_file = self.staging_dir / skill_filename
        if not staging_file.exists():
            return {"ok": False, "error": "Skill introuvable en staging"}

        # 1. Validation AST statique
        is_safe, errors = self.validate_skill(staging_file)
        if not is_safe:
            archive_target = self.archive_dir / f"rejected_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{skill_filename}"
            staging_file.rename(archive_target)
            return {"ok": False, "error": "Échec de validation AST", "violations": errors}

        active_target = self.active_dir / skill_filename
        backup_target = self.archive_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{skill_filename}"

        module_name = active_target.stem

        try:
            # 2. Sauvegarde de la version active AVANT le test
            if active_target.exists():
                shutil.copy2(active_target, backup_target)

            # 3. SMOKE TEST ISOLÉ (Subprocess avec timeout)
            # Évalue le module de staging dans un process séparé pour éviter de corrompre le Kernel E-ZZIO
            smoke_cmd = f"import sys, runpy; sys.path.insert(0, r'{str(self.active_dir.resolve())}'); runpy.run_path(r'{str(staging_file.resolve())}')"
            try:
                result = subprocess.run([sys.executable, "-c", smoke_cmd], capture_output=True, text=True, timeout=3)
                if result.returncode != 0:
                    raise Exception(f"Subprocess exit code {result.returncode}: {result.stderr}")
            except subprocess.TimeoutExpired:
                raise Exception("Smoke test timeout : Boucle infinie ou appel réseau bloquant détecté.")

            # 4. Préparation et Remplacement Atomique
            temp_target = active_target.with_suffix(".pending")
            staging_file.rename(temp_target)
            os.replace(temp_target, active_target)

            # 5. Hot-Reload dans le noyau
            if module_name in sys.modules:
                module = importlib.reload(sys.modules[module_name])
            else:
                spec = importlib.util.spec_from_file_location(module_name, str(active_target))
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

            self.loaded_skills[module_name] = module
            return {"ok": True, "module": module_name, "status": "Promu et validé avec succès"}

        except Exception as e:
            # ROLLBACK
            if "temp_target" in locals() and temp_target.exists():
                crash_target = self.archive_dir / f"crashed_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{skill_filename}"
                temp_target.rename(crash_target)
            elif staging_file.exists():
                crash_target = self.archive_dir / f"crashed_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{skill_filename}"
                staging_file.rename(crash_target)

            if backup_target.exists():
                if active_target.exists():
                    active_target.unlink()
                shutil.copy2(backup_target, active_target)
                try:
                    if module_name in sys.modules:
                        importlib.reload(sys.modules[module_name])
                except:
                    pass

            return {"ok": False, "error": f"Échec lors du Smoke Test ou du Reload (Rollback atomique effectué) : {str(e)}"}

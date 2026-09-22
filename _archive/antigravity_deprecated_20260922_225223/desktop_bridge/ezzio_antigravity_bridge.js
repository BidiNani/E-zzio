const readline = require("readline");

// stdout est réservé au protocole JSON.
// Les logs internes du package vont vers stderr.
const originalConsoleLog = console.log;
console.log = (...args) => {
    process.stderr.write(args.map(String).join(" ") + "\n");
};

const { AntigravityClient } = require("antigravity-client");

let client = null;
const cascades = new Map();
const cascadeTrackers = new Map();

async function ensureClient() {
    if (!client) {
        client = await AntigravityClient.connect();
    }
    return client;
}

async function handle(command) {
    switch (command.action) {
        case "create_cascade": {
            const c = await ensureClient();
            const cascade = await c.startCascade();
            const cascadeId = cascade.cascadeId;

            if (!cascadeId) {
                throw new Error("STARTCASCADE_RETURNED_EMPTY_CASCADE_ID");
            }

            const tracker = {
                fullText: "",
                done: false,
                donePromise: null,
                resolveDone: null,
                rejectDone: null,
            };

            tracker.donePromise = new Promise((resolve, reject) => {
                tracker.resolveDone = resolve;
                tracker.rejectDone = reject;
            });

            const textHandler = (event) => {
                if (event && typeof event.fullText === "string") {
                    tracker.fullText = event.fullText;
                }
                else if (event && typeof event.delta === "string") {
                    tracker.fullText += event.delta;
                }
            };

            const doneHandler = () => {
                tracker.done = true;
                tracker.resolveDone();
                cascade.off("done", doneHandler);
            };

            cascade.on("text", textHandler);
            cascade.on("done", doneHandler);

            cascades.set(cascadeId, cascade);
            cascadeTrackers.set(cascadeId, {
                tracker,
                textHandler,
                doneHandler,
            });

            // Maintain the reactive stream for this cascade.
            void cascade.listen().catch((error) => {
                tracker.rejectDone(error);
                process.stderr.write(
                    `[cascade:${cascadeId}] listener error: ${error?.message ?? String(error)}\n`
                );
            });

            return {
                ok: true,
                cascadeId
            };
        }
        case "status": {
            const cascade = cascades.get(command.cascadeId);

            if (!cascade) {
                return {
                    ok: false,
                    error: "CASCADE_NOT_FOUND"
                };
            }

            return {
                ok: true,
                cascadeId: command.cascadeId,
                status: cascade.state?.status ?? null
            };
        }

        case "send_message": {
            const cascade = cascades.get(command.cascadeId);

            if (!cascade) {
                return {
                    ok: false,
                    error: "CASCADE_NOT_FOUND"
                };
            }

            if (typeof command.text !== "string" || !command.text.trim()) {
                return {
                    ok: false,
                    error: "TEXT_REQUIRED"
                };
            }

            const options = {};

            if (typeof command.model === "string" && command.model.trim()) {
                options.model = command.model.trim();
            }
            else if (typeof command.model === "number") {
                options.model = command.model;
            }

            await cascade.sendMessage(command.text, options);

            return {
                ok: true,
                cascadeId: command.cascadeId,
                accepted: true
            };
        }
        case "await_result": {
            const cascade = cascades.get(command.cascadeId);
            const entry = cascadeTrackers.get(command.cascadeId);

            if (!cascade || !entry) {
                return {
                    ok: false,
                    error: "CASCADE_NOT_FOUND"
                };
            }

            const history = await cascade.getHistory();
            const steps = history?.trajectory?.steps ?? [];

            let lastStep = null;

            if (Array.isArray(steps) && steps.length > 0) {
                lastStep = steps[steps.length - 1];
            }

            let serializedStep = null;

            if (lastStep !== null) {
                try {
                    serializedStep = JSON.parse(
                        JSON.stringify(lastStep)
                    );
                }
                catch (error) {
                    serializedStep = {
                        serialization_error:
                            error?.message ?? String(error)
                    };
                }
            }

            return {
                ok: true,
                cascadeId: command.cascadeId,
                done: entry.tracker.done,
                status: cascade.state?.status ?? null,
                text: entry.tracker.fullText,
                stepCount: Array.isArray(steps) ? steps.length : 0,
                lastStep: serializedStep
            };
        }
        case "history_detail": {
            const cascade = cascades.get(command.cascadeId);

            if (!cascade) {
                return {
                    ok: false,
                    error: "CASCADE_NOT_FOUND"
                };
            }

            const history = await cascade.getHistory();
            const steps = history?.trajectory?.steps ?? [];

            if (!Array.isArray(steps)) {
                return {
                    ok: false,
                    error: "HISTORY_STEPS_INVALID"
                };
            }

            const lastStep = steps.length > 0
                ? steps[steps.length - 1]
                : null;

            let serializedStep = null;

            if (lastStep !== null) {
                try {
                    serializedStep = JSON.parse(
                        JSON.stringify(lastStep)
                    );
                } catch (error) {
                    serializedStep = {
                        serialization_error:
                            error?.message ?? String(error),
                        keys: Object.keys(lastStep ?? {})
                    };
                }
            }

            return {
                ok: true,
                cascadeId: command.cascadeId,
                stepCount: steps.length,
                lastStep: serializedStep
            };
        }
        case "history": {
            const cascade = cascades.get(command.cascadeId);

            if (!cascade) {
                return {
                    ok: false,
                    error: "CASCADE_NOT_FOUND"
                };
            }

            const history = await cascade.getHistory();

            return {
                ok: true,
                cascadeId: command.cascadeId,
                stepCount: history?.trajectory?.steps?.length ?? 0,
                hasTrajectory: !!history?.trajectory
            };
        }

        case "dispose_cascade": {
            const cascade = cascades.get(command.cascadeId);

            if (!cascade) {
                return {
                    ok: false,
                    error: "CASCADE_NOT_FOUND"
                };
            }

            const entry = cascadeTrackers.get(command.cascadeId);

            if (entry) {
                cascade.off("text", entry.textHandler);
                cascade.off("done", entry.doneHandler);
                cascadeTrackers.delete(command.cascadeId);
            }

            cascade.dispose();
            cascades.delete(command.cascadeId);

            return {
                ok: true,
                cascadeId: command.cascadeId,
                disposed: true
            };
        }

        case "models": {
            const c = await ensureClient();

            return {
                ok: true,
                models: await c.getAvailableModels()
            };
        }

        case "resolve_model": {
            const c = await ensureClient();

            return {
                ok: true,
                modelId: await c.resolveModelId(command.model)
            };
        }

        case "shutdown": {
            for (const cascade of cascades.values()) {
                try {
                    cascade.dispose();
                } catch {}
            }

            cascades.clear();

            if (client) {
                try {
                    client.dispose();
                } catch {}
            }

            client = null;

            return {
                ok: true,
                shutdown: true
            };
        }

        default:
            return {
                ok: false,
                error: `UNKNOWN_ACTION:${command.action}`
            };
    }
}

let queue = Promise.resolve();

const rl = readline.createInterface({
    input: process.stdin,
    crlfDelay: Infinity
});

rl.on("line", (line) => {
    if (!line.trim()) return;

    queue = queue.then(async () => {
        let result;

        try {
            result = await handle(JSON.parse(line));
        } catch (error) {
            result = {
                ok: false,
                error: error?.message ?? String(error)
            };
        }

        process.stdout.write(JSON.stringify(result) + "\n");
    });
});

async function shutdownProcess() {
    try {
        await queue;
        await handle({ action: "shutdown" });
    } finally {
        process.exit(0);
    }
}

process.on("SIGINT", shutdownProcess);
process.on("SIGTERM", shutdownProcess);




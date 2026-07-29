<script>
    import axios from 'axios';
    let message = $state("");
    let reponse = $state("En attente de tes instructions...");
    let loading = $state(false);

    async function envoyer() {
        if (!message) return;
        loading = true;
        try {
            const res = await axios.post('http://localhost:8000/chat', { text: message });
            reponse = res.data.response;
        } catch (error) {
            reponse = "Erreur de connexion : Vérifie que le serveur Python tourne.";
        }
        loading = false;
    }
</script>

<div class="min-h-screen bg-gray-900 text-white p-8 flex flex-col items-center">
    <h1 class="text-3xl font-bold mb-6 text-blue-400">E-zzio Control Center</h1>
    
    <div class="w-full max-w-2xl bg-gray-800 p-6 rounded-xl shadow-2xl border border-gray-700">
        <textarea bind:value={message} class="w-full p-4 bg-gray-900 border border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" rows="3" placeholder="Parle à E-zzio..."></textarea>
        
        <button onclick={envoyer} disabled={loading} class="mt-4 w-full py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-bold transition-all disabled:opacity-50">
            {loading ? "E-zzio traite l'information..." : "Envoyer"}
        </button>
    </div>

    <div class="w-full max-w-2xl mt-6 p-6 bg-gray-800 rounded-xl border border-gray-700">
        <h3 class="text-blue-400 font-semibold mb-2">Réponse :</h3>
        <p class="leading-relaxed whitespace-pre-line">{reponse}</p>
    </div>
</div>
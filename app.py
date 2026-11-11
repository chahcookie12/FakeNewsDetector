from flask import Flask, render_template, request, jsonify
import random

app = Flask(__name__)

# Route pour servir l'interface HTML
@app.route('/')
def home():
    return render_template('index.html')

# Endpoint 1 : Statut du système (Base de données et Moteur)
@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "db_available": True,
        "similarity_available": True
    })

# Endpoint 2 : Simulation de l'analyse NLP (Remplace par ton code PFA)
@app.route('/analyse', methods=['POST'])
def analyse():
    data = request.json
    contenu = data.get('contenu', '')
    
    # Ici, tu brancheras ton modèle NLP actuel.
    # Pour l'instant, on simule une réponse basée sur la longueur du texte.
    
    # Logique bidon pour la démo
    if "urgent" in contenu.lower() or "choc" in contenu.lower():
        verdict = "FAKE"
        score = 25
    elif len(contenu) > 200:
        verdict = "FIABLE"
        score = 85
    else:
        verdict = "DOUTEUX"
        score = 55
        
    response = {
        "verdict": verdict,
        "score": score,
        "indicateurs": {
            "nb_mots": len(contenu.split()),
            "nb_mots_uniques": len(set(contenu.split())),
            "sources_presentes": "http" in contenu,
            "mots_suspects": ["urgent", "complot"] if verdict == "FAKE" else []
        },
        "detail": [
            "50 Score de base",
            f"{'+35' if score > 50 else '-15'} Analyse sémantique",
            "-10 Titre sensationnaliste" if verdict == "FAKE" else "+5 Structure cohérente"
        ],
        "similarite": {
            "disponible": True,
            "correspondances": [
                {"label": "fake", "titre": "Alerte : Le gouvernement cache la vérité", "pourcentage": 88}
            ] if verdict == "FAKE" else []
        },
        "saved_id": random.randint(1000, 9999)
    }
    
    return jsonify(response)

# Endpoint 3 : Historique des analyses
@app.route('/historique', methods=['GET'])
def historique():
    # Historique factice
    return jsonify([
        {"verdict": "FIABLE", "titre": "Nouvelles mesures économiques", "score": 92, "date": "2026-06-24"},
        {"verdict": "FAKE", "titre": "La fin du monde annoncée pour demain", "score": 12, "date": "2026-06-23"},
        {"verdict": "DOUTEUX", "titre": "Des extraterrestres au Maroc ?", "score": 45, "date": "2026-06-22"}
    ])

if __name__ == '__main__':
    app.run(debug=True, port=5000)
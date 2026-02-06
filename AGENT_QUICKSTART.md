# 🚀 Quick Start - Modalità Agentica

## Guida Rapida all'Uso

### 1️⃣ Attivazione (30 secondi)

1. Apri la **sidebar** di DapaBot
2. Attiva il toggle **"Modalità agentica"** ✅
3. Clicca sul pulsante **⚙️** che appare accanto al toggle

### 2️⃣ Configurazione Tools (2 minuti)

Nel dialog che si apre:

**Pannello Sinistro:**
- Cerca un tool (es. "Wikipedia")
- Clicca sul pulsante **⚙️** accanto al tool

**Pannello Destro:**
- Configura i parametri (es. `lang: it`, `top_k_results: 3`)
- Clicca **💾 Salva Tool**
- Clicca **✅ Salva e Chiudi**

### 3️⃣ Utilizzo (immediato)

Invia un messaggio che richiede l'uso del tool:

```
"Cerca informazioni su Leonardo da Vinci su Wikipedia"
```

Vedrai:
- 🔧 Caricamento tools
- 🧠 Analisi del problema
- 🔧 Utilizzo tool: WikipediaQueryRun
- ✅ Risposta generata

## 🎯 Esempi Pratici

### Esempio 1: Ricerca Wikipedia
```
Tool: WikipediaQueryRun
Parametri: lang=it, top_k_results=3
Prompt: "Dimmi chi era Dante Alighieri"
```

### Esempio 2: Ricerca Scientifica
```
Tool: ArxivQueryRun
Parametri: max_results=5
Prompt: "Trova articoli recenti sul machine learning"
```

### Esempio 3: Calcoli Matematici
```
Tool: WolframAlphaQueryRun
Parametri: (default)
Prompt: "Calcola l'integrale di x^2 da 0 a 10"
```

## ⚠️ Note Importanti

- ✅ Solo la risposta finale viene salvata nella cronologia
- ✅ I messaggi intermedi dell'agent non inquinano lo storico
- ✅ Puoi configurare più tools contemporaneamente
- ⚠️ Alcuni tools richiedono API keys aggiuntive
- ⚠️ L'esecuzione può richiedere più tempo del normale

## 🔧 Gestione Configurazione

### Esportare
1. Apri dialog configurazione tools
2. Clicca **📤 Esporta configurazione**
3. Scarica il file JSON

### Importare
1. Apri dialog configurazione tools
2. Clicca **📥 Importa configurazione**
3. Seleziona il file JSON
4. Clicca **Importa**

### Eliminare
1. Apri dialog configurazione tools
2. Clicca **🗑️ Elimina database**
3. Conferma cliccando di nuovo

## 🆘 Risoluzione Problemi

**Tool non trovato?**
→ Verifica che `langchain-community` sia installato

**Agent non risponde?**
→ Controlla che l'API key sia valida e il modello selezionato

**Errore nei parametri?**
→ Verifica la documentazione del tool specifico

## 📖 Documentazione Completa

Per maggiori dettagli, consulta `AGENT_IMPLEMENTATION.md`
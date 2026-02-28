# 🤖 DAPABot

**DAPABot** è un chatbot avanzato multimodello, multiprovider e multimodale costruito con LangChain e Streamlit.

## ✨ Caratteristiche principali

- **🔄 Multimodello**: Supporta diversi modelli di linguaggio (LLM) nella stessa applicazione
- **🌐 Multiprovider**: Integrazione con HuggingFace, OpenRouter, Replicate
- **📁 Multimodale**: Gestisce testo, immagini, video, audio e documenti
- **🔍 RAG**: Retrieval Augmented Generation con ChromaDB e Docling
- **🤖 Modalità Agentica**: Tools nativi LangChain (Wikipedia, arXiv, GitHub, Filesystem)
- **🔌 MCP**: Supporto Model Context Protocol per estensioni esterne
- **💾 Persistenza**: Database SQLite con Peewee ORM
- **🎨 Interfaccia moderna**: UI web con Streamlit

## 🚀 Quick Start

### Installazione locale

```bash
# Clona il repository
git clone https://github.com/tuouser/Dapabot.git
cd Dapabot

# Installa le dipendenze
pip install uv
uv sync

# Avvia l'applicazione
uv run streamlit run dapabot.py
```

Apri il browser all'indirizzo: `http://localhost:8501`

### Installazione con Docker/Podman

```bash
# Build dell'immagine
podman build -t dapabot:latest -f Containerfile .

# Avvia il container
podman run -d \
  --name dapabot \
  -p 8501:8501 \
  -p 6969:6969 \
  -v $(pwd)/config.db:/app/dapabot/config.db \
  -v $(pwd)/uploads:/app/dapabot/uploads \
  -v $(pwd)/vectorstore_cache:/app/dapabot/vectorstore_cache \
  dapabot:latest
```

## 📚 Documentazione

La documentazione completa è disponibile in due modi:

1. **Dall'interfaccia**: Clicca sul pulsante "📖 Manuale Utente" in fondo alla sidebar
2. **File Markdown**: Consulta il [Manuale Utente](docs/Manuale_Utente_DAPABot.md) nella directory `docs/`

Il manuale include:
- Introduzione e tecnologie utilizzate
- Installazione (locale e container)
- Utilizzo delle funzionalità (Chat, RAG, Modalità Agentica, MCP)
- Guida per lo sviluppatore con diagrammi
- Struttura del database

## 🛠️ Tecnologie utilizzate

- **[LangChain](https://www.langchain.com/)**: Framework per LLM e agenti
- **[Streamlit](https://streamlit.io/)**: Interfaccia web interattiva
- **[Docling](https://github.com/DS4SD/docling)**: Elaborazione documenti PDF/DOCX
- **[ChromaDB](https://www.trychroma.com/)**: Vector database per RAG
- **[Peewee](http://docs.peewee-orm.com/)**: ORM per SQLite
- **[MCP](https://modelcontextprotocol.io/)**: Model Context Protocol

## 📋 Requisiti

- Python 3.13 o superiore
- 4GB RAM minimo (8GB consigliato)
- Spazio disco: ~2GB per dipendenze

## 🎯 Funzionalità

### RAG (Retrieval Augmented Generation)
Carica documenti (PDF, DOCX, TXT, immagini) e fai domande basate sul loro contenuto.

### Modalità Agentica
Abilita i modelli a usare strumenti esterni:
- **Wikipedia**: Ricerca informazioni
- **arXiv**: Cerca articoli scientifici
- **GitHub**: Interagisce con repository
- **Filesystem**: Legge/scrive file
- **altri in arrivo...**

### Server MCP
Estendi le capacità con server esterni tramite Model Context Protocol.

## 🔧 Configurazione

Al primo avvio, DAPABot crea automaticamente:
- `config.db`: Database SQLite per configurazioni e cronologia
- `uploads/`: Directory per documenti RAG
- `.chroma/`: Database vettoriale per RAG

### API Keys

Inserisci le tue API keys nell'interfaccia:
- **HuggingFace**: `hf_xxxxxxxxxxxxx`
- **OpenRouter**: `sk-or-v1-xxxxxxxxxxxxx`
- **Replicate**: `r8_xxxxxxxxxxxxx`

## 📖 Esempi d'uso

### Conversazione semplice
```
Utente: Ciao! Spiegami cosa è il machine learning.
DAPABot: Il machine learning è...
```

### Con RAG
```
1. Carica un PDF con specifiche tecniche
2. Abilita RAG
3. Utente: Quali sono le caratteristiche del prodotto X?
4. DAPABot: [risposta basata sul PDF]
```

### Con Tools
```
1. Abilita modalità agentica
2. Attiva tool Wikipedia
3. Utente: Chi era Alan Turing?
4. DAPABot: [cerca su Wikipedia e risponde]
```

## 🤝 Contribuire

Contributi benvenuti! Leggi la [Guida per Contribuire](CONTRIBUTING.md) per sapere come partecipare allo sviluppo.

Per aggiungere nuovi provider o tools, consulta la [Guida per lo Sviluppatore](docs/Manuale_Utente_DAPABot.md#43-estendere-dapabot).

## 📄 Licenza

Questo progetto è rilasciato sotto licenza **GNU General Public License v3.0 (GPL-3.0)**.

Sei libero di:
- ✅ Usare il software per qualsiasi scopo
- ✅ Studiare come funziona e modificarlo
- ✅ Ridistribuire copie
- ✅ Distribuire versioni modificate

**Condizioni**:
- 📋 Devi rendere disponibile il codice sorgente
- 📋 Devi mantenere la stessa licenza GPL-3.0
- 📋 Devi documentare le modifiche apportate
- 📋 Devi includere una copia della licenza

Per maggiori dettagli, consulta il file [LICENSE](LICENSE) o visita https://www.gnu.org/licenses/gpl-3.0.html

## 🔗 Link utili

- **Documentazione**: [docs/](docs/)
- **LangChain**: https://python.langchain.com/
- **Streamlit**: https://docs.streamlit.io/
- **MCP**: https://modelcontextprotocol.io/

## 🐛 Segnalazione bug

Per segnalare bug o richiedere funzionalità, apri una issue su GitHub.

---

**Sviluppato con ❤️ usando LangChain e Streamlit**
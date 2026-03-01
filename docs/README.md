# Documentazione DAPABot

Benvenuto nella documentazione di DAPABot!

## 📚 Contenuti

- **[Manuale Utente](Manuale_Utente_DAPABot.md)**: Guida completa all'utilizzo di DAPABot (versione con diagrammi Mermaid per GitHub)
- **[Manuale Utente PDF](Manuale_Utente_DAPABot_PDF.md)**: Versione ottimizzata per la conversione in PDF (con diagrammi come immagini)

## 📖 Come leggere la documentazione

### Opzione 1: Visualizzazione su GitHub

La documentazione è scritta in Markdown e può essere letta direttamente su GitHub con formattazione completa, inclusi i diagrammi Mermaid.

Usa il file: **[Manuale_Utente_DAPABot.md](Manuale_Utente_DAPABot.md)**

### Opzione 2: Visualizzazione locale con un editor Markdown

Puoi aprire i file `.md` con qualsiasi editor che supporti Markdown, come:

- **Visual Studio Code** (con estensione Markdown Preview Enhanced)
- **Typora**
- **Mark Text**
- **Obsidian**

### Opzione 3: Convertire in PDF

Per generare un PDF con i diagrammi renderizzati correttamente, usa la versione PDF-friendly:

**Con Pandoc** (consigliato):
```bash
# Installa pandoc se non già presente
sudo apt install pandoc texlive-xetex  # Linux
# oppure
brew install pandoc basictex  # macOS

# Genera il PDF
pandoc docs/Manuale_Utente_DAPABot_PDF.md \
  -o docs/Manuale_Utente_DAPABot.pdf \
  --pdf-engine=xelatex \
  -V geometry:margin=2cm \
  --toc \
  --toc-depth=3 \
  -V linkcolor:blue \
  -V urlcolor:blue
```

**Con VS Code**:
1. Installa l'estensione "Markdown PDF"
2. Apri `Manuale_Utente_DAPABot_PDF.md`
3. Premi `Ctrl+Shift+P` e seleziona "Markdown PDF: Export (pdf)"

### Opzione 4: Generare HTML

**Con Pandoc**:
```bash
pandoc docs/Manuale_Utente_DAPABot_PDF.md \
  -o docs/Manuale_Utente_DAPABot.html \
  --standalone \
  --toc \
  --toc-depth=3 \
  -c https://cdn.jsdelivr.net/npm/github-markdown-css/github-markdown.min.css
```

**Con Python Markdown**:
```bash
python -m markdown Manuale_Utente_DAPABot.md > Manuale_Utente_DAPABot.html
```

## 🎨 Diagrammi

### Versione GitHub (Mermaid)
Il file `Manuale_Utente_DAPABot.md` contiene diagrammi Mermaid che vengono renderizzati automaticamente su GitHub.

### Versione PDF (Immagini PNG)
Il file `Manuale_Utente_DAPABot_PDF.md` contiene riferimenti a immagini PNG dei diagrammi, ottimizzate per la conversione in PDF.

### Rigenerare i diagrammi

Se modifichi i diagrammi Mermaid nel manuale, puoi rigenerarli con:

```bash
# Assicurati che Playwright sia installato
uv pip install playwright
python -m playwright install chromium

# Converti i diagrammi
python convert_mermaid_playwright.py
```

Questo script:
1. Estrae tutti i diagrammi Mermaid dal manuale
2. Li converte in immagini PNG usando Playwright
3. Crea una versione PDF-friendly del manuale con i riferimenti alle immagini

## 📝 Struttura della documentazione

Il Manuale Utente è organizzato in 5 capitoli principali:

1. **Introduzione**: Panoramica di DAPABot e delle tecnologie utilizzate
2. **Installazione**: Guida all'installazione locale e con container
3. **Usare DAPABot**: Tutorial completo sulle funzionalità
4. **Guida per lo Sviluppatore**: Architettura e come estendere DAPABot
5. **Appendice**: Struttura del database e dettagli tecnici

## 🖼️ Screenshot

Gli screenshot della GUI sono disponibili nella directory `images/`:

- `01_interfaccia_principale.png`: Interfaccia principale
- `02_gestione_chat.png`: Gestione Chat
- `04_modalita_agentica.png`: Modalità Agentica
- `05_tools_config.png`: Configurazione Tools
- `06_mcp_config.png`: Configurazione MCP

### Catturare nuovi screenshot

Per catturare screenshot aggiornati dell'interfaccia:

```bash
# Assicurati che DAPABot sia in esecuzione
uv run streamlit run dapabot.py

# In un altro terminale, esegui lo script
python capture_screenshots.py
```

## 📊 Diagrammi inclusi

Il manuale include 6 diagrammi:

1. **Architettura generale** - Componenti principali del sistema
2. **Sequenza: Messaggio semplice** - Flusso di un messaggio base
3. **Sequenza: Messaggio con RAG** - Flusso con Retrieval Augmented Generation
4. **Sequenza: Messaggio con Tools** - Flusso con modalità agentica
5. **Sequenza: Messaggio con MCP** - Flusso con server MCP
6. **Schema ER Database** - Struttura completa del database

Tutti i diagrammi sono disponibili come:
- Codice Mermaid nel file originale
- Immagini PNG nella directory `images/`

## 🔗 Link utili

- **Repository GitHub**: [https://github.com/tuouser/Dapabot](https://github.com/tuouser/Dapabot)
- **LangChain**: [https://python.langchain.com/](https://python.langchain.com/)
- **Streamlit**: [https://docs.streamlit.io/](https://docs.streamlit.io/)
- **Model Context Protocol**: [https://modelcontextprotocol.io/](https://modelcontextprotocol.io/)

## 📧 Supporto

Per domande, problemi o suggerimenti:
- Apri una issue su GitHub
- Consulta la documentazione di LangChain e Streamlit
- Controlla la sezione "Guida per lo Sviluppatore" per dettagli tecnici

## 📄 Licenza

La documentazione è distribuita con la stessa licenza del progetto DAPABot.

---

**Ultimo aggiornamento**: 28 Febbraio 2026
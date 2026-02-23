"""
Interfaccia GUI per la gestione dei tools in Streamlit.
Questo modulo contiene le funzioni per la configurazione e gestione dei tools
utilizzati in modalità agentica.
"""

import streamlit as st
from datetime import datetime
from src.ConfigurazioneDB import ConfigurazioneDB


def _on_close_tools_dialog():
    """
    Callback chiamato quando la dialog dei tools viene chiusa.
    Aggiorna il DB con le selezioni fatte nel multiselect.
    """
    st.session_state["tools_dialog_open"] = False
    
    # Aggiorna il DB solo se ci sono modifiche
    if "tools_selezionati_temp" in st.session_state:
        tools_selezionati = st.session_state["tools_selezionati_temp"]
        ConfigurazioneDB.aggiorna_stati_tools(tools_selezionati)
        # Ricarica i tools solo nel provider corrente
        provider_corrente = st.session_state.get("provider_corrente_dialog")
        
        # Import locale per evitare dipendenze circolari
        from src.gui_utils import _carica_tools_nei_provider
        risultato = _carica_tools_nei_provider(provider_name=provider_corrente)
        
        # Pulisci lo stato temporaneo
        del st.session_state["tools_selezionati_temp"]
        if "provider_corrente_dialog" in st.session_state:
            del st.session_state["provider_corrente_dialog"]


@st.dialog(
    "⚙️ Configurazione Tools per Agent",
    width="large",
    dismissible=True,
    on_dismiss=lambda: _on_close_tools_dialog()
)
def mostra_dialog_tools_agent():
    """
    Dialog per configurare i tools disponibili per l'agent.
    I tools sono condivisi tra tutti i provider.
    Layout con tab: Configurazione e Database.
    """
    st.caption("Configura i tools disponibili per tutti i provider")
    
    # Ottieni le istanze dei tools dal session state
    tools_instances = st.session_state.get("tools_instances", {})
    
    if not tools_instances:
        st.warning("Nessun tool disponibile. Verifica l'installazione dei tools in src/tools/")
        return
    
    # Carica i tools già configurati dal DB
    tools_salvati = ConfigurazioneDB.carica_tools()
    tools_salvati_dict = {t["nome_tool"]: t["configurazione"] for t in tools_salvati}
    
    # Inizializza lo stato della sessione per il tool selezionato
    if "selected_tool_for_config" not in st.session_state:
        st.session_state["selected_tool_for_config"] = None
    if "tool_config_temp" not in st.session_state:
        st.session_state["tool_config_temp"] = {}
    
    # Crea le tab
    tab1, tab2 = st.tabs(["⚙️ Configurazione", "🗄️ Database"])
    
    # ==================== TAB 1: CONFIGURAZIONE ====================
    with tab1:
        # Layout a due colonne
        col_left, col_right = st.columns([1, 2])
    
        with col_left:
            st.subheader("📋 Tools Disponibili")
            st.caption(f"Totale: {len(tools_instances)} tools")
            
            # Filtro di ricerca
            search_filter = st.text_input("🔍 Cerca tool", placeholder="Filtra per nome...")
            
            # Filtra i tools in base alla ricerca
            tool_names = list(tools_instances.keys())
            filtered_tools = [t for t in tool_names if search_filter.lower() in t.lower()] if search_filter else tool_names
            
            # Container scrollabile per la lista
            with st.container(height=400):
                for tool_name in sorted(filtered_tools):
                    # Pulsante che seleziona il tool quando cliccato
                    if st.button(tool_name, key=f"select_btn_{tool_name}", use_container_width=True):
                        st.session_state["selected_tool_for_config"] = tool_name
                        # Carica la configurazione esistente se presente
                        if tool_name in tools_salvati_dict:
                            st.session_state["tool_config_temp"] = tools_salvati_dict[tool_name].copy()
                        else:
                            st.session_state["tool_config_temp"] = {}
                        st.rerun()
        
        # Multiselect per selezionare tools attivi (dopo le colonne)
        st.divider()
        st.subheader("🔧 Selezione Tools Attivi")
        
        # Ottieni tutti i tools disponibili dal loader
        tutti_tools_disponibili = list(tools_instances.keys())
        
        # Ottieni i tools attivi dal DB, filtrando solo quelli che esistono ancora
        tools_attivi_db = [
            t["nome_tool"] for t in tools_salvati
            if t.get("attivo", True) and t["nome_tool"] in tutti_tools_disponibili
        ]
        
        # Inizializza lo stato se non esiste
        if "tools_selezionati_temp" not in st.session_state:
            st.session_state["tools_selezionati_temp"] = tools_attivi_db
        st.caption("ℹ️ I tools rimossi dal DB saranno usati senza configurazione")

        tools_selezionati = st.multiselect(
            "Seleziona quali tools vuoi rendere attivi",
            options=sorted(tutti_tools_disponibili),
            default=st.session_state["tools_selezionati_temp"],
            key="tools_attivi_multiselect",
            help="Solo i tools selezionati saranno disponibili per l'utilizzo in modalità agentica"
        )
        
        # Salva la selezione corrente nel session state (senza rerun)
        st.session_state["tools_selezionati_temp"] = tools_selezionati
        
        with col_right:
            st.subheader("🔧 Configurazione Tool")
            
            selected_tool = st.session_state.get("selected_tool_for_config")
            
            if not selected_tool:
                st.info("👈 Seleziona un tool dalla lista per configurarlo")
            else:
                st.markdown(f"**Tool selezionato:** `{selected_tool}`")
                
                # Ottieni l'istanza del tool
                tool_instance = tools_instances.get(selected_tool)
                
                if not tool_instance:
                    st.error(f"Tool '{selected_tool}' non trovato nelle istanze")
                    return
                
                # Ottieni la configurazione dal tool usando get_configurazione()
                tool_config = tool_instance.get_configurazione()
                
                # Separa parametri configurabili e variabili d'ambiente
                configurable_params = {k: v for k, v in tool_config.items() if not k.startswith('_')}
                variabili_ambiente = tool_config.get('_variabili_necessarie', {})
                
                # ========== SEZIONE PARAMETRI CONFIGURABILI ==========
                if configurable_params:
                    st.divider()
                    st.caption("📝 Parametri configurabili:")
                    
                    # Form dinamico basato sui parametri
                    config_temp = st.session_state["tool_config_temp"]
                    
                    for param_name, param_value in configurable_params.items():
                        # Valore corrente (da config temp o dal tool)
                        current_value = config_temp.get(param_name, param_value)
                        
                        # Crea il widget appropriato in base al tipo
                        if isinstance(param_value, bool):
                            value = st.checkbox(
                                param_name,
                                value=bool(current_value),
                                key=f"param_{selected_tool}_{param_name}"
                            )
                            config_temp[param_name] = value
                        
                        elif isinstance(param_value, int):
                            value = st.number_input(
                                param_name,
                                value=int(current_value) if current_value is not None else 0,
                                key=f"param_{selected_tool}_{param_name}"
                            )
                            config_temp[param_name] = value
                        
                        elif isinstance(param_value, float):
                            value = st.number_input(
                                param_name,
                                value=float(current_value) if current_value is not None else 0.0,
                                key=f"param_{selected_tool}_{param_name}",
                                format="%.2f"
                            )
                            config_temp[param_name] = value
                        
                        elif isinstance(param_value, list):
                            # Per liste, usa text_area con valori separati da virgola
                            list_value = ", ".join(str(v) for v in current_value) if isinstance(current_value, list) else str(current_value or "")
                            value = st.text_area(
                                param_name,
                                value=list_value,
                                help="Valori separati da virgola",
                                key=f"param_{selected_tool}_{param_name}",
                                height=100
                            )
                            # Converti in lista
                            config_temp[param_name] = [v.strip() for v in value.split(",") if v.strip()]
                        
                        else:
                            # Default: text_input per stringhe
                            value = st.text_input(
                                param_name,
                                value=str(current_value) if current_value is not None else "",
                                key=f"param_{selected_tool}_{param_name}"
                            )
                            config_temp[param_name] = value
                    
                    st.session_state["tool_config_temp"] = config_temp
                
                # ========== SEZIONE VARIABILI D'AMBIENTE ==========
                if variabili_ambiente:
                    st.divider()
                    st.caption("🔐 Variabili d'ambiente:")
                    
                    # Inizializza le variabili d'ambiente in config_temp se non presenti
                    if "_variabili_necessarie" not in st.session_state["tool_config_temp"]:
                        st.session_state["tool_config_temp"]["_variabili_necessarie"] = {}
                    
                    env_vars_temp = st.session_state["tool_config_temp"]["_variabili_necessarie"]
                    variabili_vuote = []
                    
                    for var_name, var_default in variabili_ambiente.items():
                        # Valore corrente (da config temp o dal default)
                        current_value = env_vars_temp.get(var_name, var_default)
                        
                        # Widget per la variabile d'ambiente
                        value = st.text_input(
                            var_name,
                            value=str(current_value) if current_value is not None else "",
                            key=f"env_{selected_tool}_{var_name}",
                            help=f"Variabile d'ambiente: {var_name}"
                        )
                        env_vars_temp[var_name] = value
                        
                        # Traccia le variabili vuote per il warning
                        if not value:
                            variabili_vuote.append(var_name)
                    
                    st.session_state["tool_config_temp"]["_variabili_necessarie"] = env_vars_temp
                    
                    # Mostra warning se ci sono variabili vuote
                    if variabili_vuote:
                        st.warning(f"⚠️ Variabili d'ambiente non configurate: {', '.join(variabili_vuote)}")
                
                # Se non ci sono né parametri né variabili
                if not configurable_params and not variabili_ambiente:
                    st.info("Questo tool non ha parametri configurabili né variabili d'ambiente.")
                    st.caption("Puoi comunque salvarlo per renderlo disponibile all'agent.")
                
                st.divider()
                
                # Pulsanti di azione
                col_save, col_remove, col_cancel = st.columns(3)
                
                with col_save:
                    if st.button("💾 Salva Tool", type="primary", use_container_width=True, help="Salva la configurazione del tool nel DB"):
                        try:
                            # Aggiorna l'istanza del tool con i nuovi valori
                            for key, value in st.session_state["tool_config_temp"].items():
                                if key == "_variabili_necessarie":
                                    # Gestisce le variabili d'ambiente
                                    tool_instance.set_variabili_necessarie(value)
                                elif hasattr(tool_instance, key):
                                    setattr(tool_instance, key, value)
                            
                            # Salva nel database
                            ConfigurazioneDB.salva_tool(
                                nome_tool=selected_tool,
                                configurazione=st.session_state["tool_config_temp"]
                            )
                            st.success(f"✅ Tool '{selected_tool}' salvato!")
                            st.session_state["selected_tool_for_config"] = None
                            st.session_state["tool_config_temp"] = {}
                            st.rerun()
                        except Exception as e:
                            st.error(f"Errore nel salvataggio: {e}")
                
                with col_remove:
                    if selected_tool in tools_salvati_dict:
                        if st.button("❌ Rimuovi Tool", use_container_width=True, help="Rimuove la configurazione del tool dal DB. Se si attiva il tool, verrà usato senza configurazione"):
                            try:
                                ConfigurazioneDB.cancella_tool(selected_tool)
                                st.success(f"🗑️ Tool '{selected_tool}' rimosso!")
                                st.session_state["selected_tool_for_config"] = None
                                st.session_state["tool_config_temp"] = {}
                                st.rerun()
                            except Exception as e:
                                st.error(f"Errore nella rimozione: {e}")
                
                with col_cancel:
                    if st.button("↩️ Annulla", use_container_width=True):
                        st.session_state["selected_tool_for_config"] = None
                        st.session_state["tool_config_temp"] = {}
                        st.rerun()
    
    # ==================== TAB 2: DATABASE ====================
    with tab2:
        st.subheader("🗄️ Gestione Database")
        st.caption("Importa, esporta o elimina la configurazione dei tools")
        
        col_import, col_export, col_delete = st.columns(3)
        
        with col_import:
            st.markdown("### 📥 Importa Tools")
            uploaded_file = st.file_uploader("Seleziona file JSON", type=["json"], key="import_agent_db")
            if uploaded_file and st.button("Importa configurazione tools", key="btn_import_agent_db", use_container_width=True):
                try:
                    import json
                    json_data = uploaded_file.read().decode("utf-8")
                    data = json.loads(json_data)
                    
                    # Importa solo i tools dal JSON
                    if "tools" in data:
                        for tool_data in data["tools"]:
                            ConfigurazioneDB.salva_tool(
                                nome_tool=tool_data["nome_tool"],
                                configurazione=tool_data["configurazione"],
                                attivo=tool_data.get("attivo", True)
                            )
                        st.success(f"✅ Importati {len(data['tools'])} tools!")
                        st.rerun()
                    else:
                        st.warning("Il file JSON non contiene dati sui tools")
                except Exception as e:
                    st.error(f"Errore nell'importazione: {e}")
            st.caption("ℹ️ Importa solo la configurazione dei tools")
        
        with col_export:
            st.markdown("### 📤 Esporta Tools")
            if st.button("Esporta configurazione tools", key="btn_export_agent_db", use_container_width=True):
                try:
                    json_data = ConfigurazioneDB.esporta_json()
                    filename = f"tools-config-{datetime.now().strftime('%Y%m%d')}.json"
                    st.download_button(
                        label="⬇️ Scarica file",
                        data=json_data,
                        file_name=filename,
                        mime="application/json",
                        key="download_agent_db",
                        use_container_width=True
                    )
                    st.caption("ℹ️ Esporta solo la configurazione dei tools")
                except Exception as e:
                    st.error(f"Errore nell'esportazione: {e}")
        
        with col_delete:
            st.markdown("### 🗑️ Elimina Tools")
            if st.button("Elimina tutti i tools", key="btn_delete_agent_db", use_container_width=True, type="secondary"):
                if st.session_state.get("confirm_delete_agent_db", False):
                    try:
                        ConfigurazioneDB.elimina_tutti_tools()
                        # Svuota i tools da tutti i provider
                        providers = st.session_state.get("providers", {})
                        for provider in providers.values():
                            provider.set_tools([])
                            try:
                                provider._crea_agent()
                            except:
                                pass  # Ignora errori durante la ricreazione dell'agent
                        st.success("✅ Tutti i tools eliminati e rimossi dai provider!")
                        st.session_state["confirm_delete_agent_db"] = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore nell'eliminazione: {e}")
                else:
                    st.session_state["confirm_delete_agent_db"] = True
                    st.warning("⚠️ Clicca di nuovo per confermare l'eliminazione di tutti i tools")
            st.caption("ℹ️ Elimina solo i tools dalla tabella tool")
        
        st.divider()
        
        # Informazioni sul database
        st.markdown("### ℹ️ Informazioni")
        tools_salvati_count = len(ConfigurazioneDB.carica_tools())
        st.info(f"**Tools configurati nel database:** {tools_salvati_count}")
        
        if tools_salvati_count > 0:
            with st.expander("📋 Dettagli tools salvati"):
                for tool in ConfigurazioneDB.carica_tools():
                    st.write(f"• **{tool['nome_tool']}**")
                    config = tool['configurazione']
                    if config:
                        st.json(config)
    
    st.divider()
    
    # Pulsante chiudi (fuori dalle tab, sempre visibile)
    if st.button("✅ Chiudi", type="primary", use_container_width=True):
        # Chiama la stessa funzione del callback on_dismiss
        _on_close_tools_dialog()
        st.rerun()


# Made with Bob
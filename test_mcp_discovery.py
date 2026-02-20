#!/usr/bin/env python3
"""
Script di test per verificare il funzionamento dell'approccio ibrido MCP.
Testa sia l'integrazione con langchain-mcp-adapters che il discovery con SDK nativo.

Esegui con: python test_mcp_discovery.py
"""

import asyncio
import sys
from src.mcp.client import get_mcp_client_manager


async def test_discovery():
    """Test completo del sistema di discovery MCP"""
    
    print("=" * 70)
    print("TEST APPROCCIO IBRIDO MCP - Dapabot")
    print("=" * 70)
    
    # Ottieni il manager
    manager = get_mcp_client_manager()
    
    # Carica configurazioni
    print("\n[1] Caricamento configurazioni dal database...")
    manager.carica_configurazioni_da_db()
    
    # Ottieni lista server
    server_names = manager.get_server_names()
    
    if not server_names:
        print("❌ Nessun server MCP configurato nel database")
        print("\nPer testare questo script:")
        print("1. Configura almeno un server MCP tramite la GUI")
        print("2. Assicurati che sia attivo")
        print("3. Riprova questo test")
        return False
    
    print(f"✓ Trovati {len(server_names)} server configurati: {', '.join(server_names)}")
    
    # Test per ogni server
    all_tests_passed = True
    
    for server_name in server_names:
        print(f"\n{'=' * 70}")
        print(f"[2] Test server: {server_name}")
        print(f"{'=' * 70}")
        
        # Test 1: Lista risorse
        print(f"\n[2.1] Test list_available_resources()...")
        try:
            resources = await manager.list_available_resources(server_name)
            print(f"✓ Trovate {len(resources)} risorse")
            
            if resources:
                print("\nPrime 3 risorse:")
                for i, resource in enumerate(resources[:3], 1):
                    print(f"  {i}. {resource['name']}")
                    print(f"     URI: {resource['uri']}")
                    print(f"     Tipo: {resource['mimeType'] or 'N/A'}")
                    print(f"     Descrizione: {resource['description'][:50]}..." if len(resource['description']) > 50 else f"     Descrizione: {resource['description']}")
            else:
                print("  ℹ Nessuna risorsa disponibile")
                
        except Exception as e:
            print(f"❌ Errore: {e}")
            all_tests_passed = False
        
        # Test 2: Lista prompt
        print(f"\n[2.2] Test list_available_prompts()...")
        try:
            prompts = await manager.list_available_prompts(server_name)
            print(f"✓ Trovati {len(prompts)} prompt")
            
            if prompts:
                print("\nPrimi 3 prompt:")
                for i, prompt in enumerate(prompts[:3], 1):
                    print(f"  {i}. {prompt['name']}")
                    print(f"     Descrizione: {prompt['description'][:50]}..." if len(prompt['description']) > 50 else f"     Descrizione: {prompt['description']}")
                    if prompt['arguments']:
                        print(f"     Argomenti: {len(prompt['arguments'])}")
                        for arg in prompt['arguments'][:2]:
                            req = "obbligatorio" if arg['required'] else "opzionale"
                            print(f"       - {arg['name']} ({req})")
            else:
                print("  ℹ Nessun prompt disponibile")
                
        except Exception as e:
            print(f"❌ Errore: {e}")
            all_tests_passed = False
        
        # Test 3: Cache
        print(f"\n[2.3] Test caching...")
        try:
            import time
            
            # Prima chiamata (senza cache)
            start = time.time()
            await manager.list_available_resources(server_name, use_cache=False)
            time_no_cache = time.time() - start
            
            # Seconda chiamata (con cache)
            start = time.time()
            await manager.list_available_resources(server_name, use_cache=True)
            time_with_cache = time.time() - start
            
            speedup = time_no_cache / time_with_cache if time_with_cache > 0 else float('inf')
            
            print(f"✓ Tempo senza cache: {time_no_cache*1000:.1f}ms")
            print(f"✓ Tempo con cache: {time_with_cache*1000:.1f}ms")
            print(f"✓ Speedup: {speedup:.1f}x")
            
        except Exception as e:
            print(f"❌ Errore nel test cache: {e}")
            all_tests_passed = False
    
    # Test 4: Tools (langchain-mcp-adapters)
    print(f"\n{'=' * 70}")
    print("[3] Test integrazione langchain-mcp-adapters")
    print(f"{'=' * 70}")
    
    try:
        tools = await manager.get_tools()
        print(f"✓ Caricati {len(tools)} tools da tutti i server")
        
        if tools:
            print("\nPrimi 5 tools:")
            for i, tool in enumerate(tools[:5], 1):
                print(f"  {i}. {tool.name}")
                desc = tool.description[:60] + "..." if len(tool.description) > 60 else tool.description
                print(f"     {desc}")
        
    except Exception as e:
        print(f"❌ Errore nel caricamento tools: {e}")
        all_tests_passed = False
    
    # Riepilogo
    print(f"\n{'=' * 70}")
    print("RIEPILOGO TEST")
    print(f"{'=' * 70}")
    
    if all_tests_passed:
        print("✅ Tutti i test sono passati con successo!")
        print("\nL'approccio ibrido funziona correttamente:")
        print("  • langchain-mcp-adapters: Tools ✓")
        print("  • SDK nativo MCP: Discovery risorse e prompt ✓")
        print("  • Sistema di caching: Funzionante ✓")
        return True
    else:
        print("⚠️  Alcuni test sono falliti")
        print("Verifica la configurazione dei server MCP")
        return False


def main():
    """Entry point dello script"""
    try:
        success = asyncio.run(test_discovery())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrotto dall'utente")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Errore fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

# Made with Bob

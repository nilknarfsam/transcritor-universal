# Relatório de Limpeza da Interface — Sprint UX 3.1

**Data:** 2026-05-29  
**Versão UI:** 3.0.4 — Simplificação Radical  
**Objetivo:** Fila de transcrição como foco absoluto da janela principal.

---

## Resumo executivo

A interface principal do CortexFlow foi reduzida a três zonas: **toolbar superior**, **fila de arquivos** (~85% da área útil) e **status bar inferior**. Configurações e visualização de resultado foram movidas para janelas modais/secundárias sob demanda.

---

## Arquivos movidos para `src/ui/legacy_ui/`

| Arquivo | Descrição |
|---------|-----------|
| `knowledge_workspace_panel.py` | Workspace premium de conhecimento (busca unificada, cards) |
| `library_panel.py` | Painel de biblioteca / catálogo |
| `graph_panel.py` | Grafo de conexões entre documentos |
| `study_panel.py` | Modo estudo (flashcards, quizzes) |
| `dataset_panel.py` | Gestão de datasets exportáveis |

Esses painéis **não são montados** na janela principal. Permanecem no repositório para reutilização futura ou ferramentas internas.

---

## Arquivos novos

| Arquivo | Função |
|---------|--------|
| `src/ui/settings_modal.py` | Modal de configurações (substitui aba dedicada) |
| `src/ui/result_window.py` | Janela secundária para visualizar/exportar resultado |
| `src/ui/legacy_ui/__init__.py` | Pacote de painéis arquivados |

---

## Componentes removidos da tela principal

| Componente | Antes | Depois |
|------------|-------|--------|
| `BrandSidebar` | Barra lateral com marca, versão, navegação | **Removida** — classe excluída de `settings_panel.py` |
| Header de marca | Título + slogan no topo do conteúdo | **Removido** — título apenas na barra do SO |
| `ResultPanel` embutido | Painel lateral ~30% da largura | **Removido** — substituído por botão «Visualizar Resultado» |
| Aba Configurações | View alternativa em `view_host` | **Removida** — modal via toolbar |
| Toolbar interna da fila | Botões duplicados dentro do `QueuePanel` | **Removida** — centralizada na toolbar principal |
| Barra de progresso global | Acima da fila | **Removida** — progresso por linha + status bar |
| `JobDetailsPanel` expandido | 8 campos incluindo caminhos completos | **Compactado** — Nome, Status, Cache, Saída |

---

## Arquivos UI não utilizados na janela principal (órfãos)

| Arquivo | Status | Observação |
|---------|--------|------------|
| `src/ui/result_panel.py` | **Arquivado funcionalmente** | Lógica migrada para `result_window.py`; arquivo mantido no repo |
| `src/ui/document_detail_panel.py` | **Legado** | Usado apenas por `legacy_ui/knowledge_workspace_panel.py` |
| `src/ui/components/knowledge_widgets.py` | **Legado** | Usado apenas pelos painéis em `legacy_ui/` |
| `src/ui/legacy_ui/*.py` | **Arquivado** | Não importados por `main_window.py` |

Nenhum arquivo foi **apagado** nesta sprint — apenas desacoplados da shell principal.

---

## Imports órfãos removidos

| Arquivo | Import removido |
|---------|-----------------|
| `src/ui/main_window.py` | `ResultPanel`, `BrandSidebar`, `AppSettingsPanel` (view embutida) |

---

## Layout final da janela principal

```
┌─────────────────────────────────────────────────────────────┐
│ [Adicionar Arquivos] [Adicionar Pasta] [Remover] [Limpar]   │
│ [▶ INICIAR TRANSCRIÇÃO] [⏹ Cancelar] [📂 Abrir] [⚙ Config] │
├─────────────────────────────────────────────────────────────┤
│  Fila (Arquivo | Tipo | Status | Progresso | Saída | Tempo) │
│  ─────────────────────────────────────────────────────────  │
│  (lista scrollável — ~85% da área)                          │
│  Detalhes compactos: Nome | Status | Cache | Saída          │
│  [Visualizar Resultado]                                     │
├─────────────────────────────────────────────────────────────┤
│ Total: X | Aguardando: X | Processando: X | Concluídos: X   │
└─────────────────────────────────────────────────────────────┘
```

---

## Configurações preservadas na modal

**Visíveis por padrão:** Tema, Idioma, Formato padrão, Modo exportação, Tipo conteúdo, Pasta saída.

**Recolhidas em «Configurações avançadas»:** Pipeline de conhecimento, workspace, coleção, autor, speaker, categoria, tags, tipo de conhecimento, restaurar fila, limpar cache, histórico recente.

---

## Riscos e próximos passos

1. **`result_panel.py`** — candidato a mover para `legacy_ui/` ou remover em sprint futura após validação.
2. **Atalhos** — `Ctrl+E` exporta via janela de resultado (precisa estar aberta); considerar export direto do item selecionado.
3. **Testes E2E** — não há testes automatizados de GUI; validação manual recomendada.
4. **README.md** — estrutura de pastas ainda referencia painéis na raiz de `src/ui/`; atualizar em sprint de documentação.

---

## Commits desta sprint

1. `refactor: simplificar interface focando na fila de transcrição`
2. `style: remover sidebar e ampliar área útil`
3. `chore: arquivar painéis avançados em legacy_ui`
4. `docs: adicionar relatório de limpeza da interface`

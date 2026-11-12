# 🖱️ DualPointer Pro

> **Gerenciador Avançado de Multi-Mouse e Multi-Monitor para Windows**  
> Desenvolvido por **Caio Monteiro** ([@chacalbl4ck](https://github.com/chacalbl4ck))

---

## 📋 Sobre o Projeto

O **DualPointer Pro** é um software de alta performance desenvolvido em Python para Windows que permite conectar **dois mouses físicos** simultaneamente ao mesmo computador, separando seus movimentos, cliques e delimitando as telas/monitores onde cada um pode operar, **sem que um interfira no movimento ou nos cliques do outro**.

Com suporte nativo a múltiplos monitores, personalização visual de ponteiros (design, cor, aura glow e tamanho), identificação por **USB Hardware ID (VID & PID)** e integração direta com a **pasta Inicializar do Windows**.

---

## ✨ Principais Funcionalidades

- **Controle Simultâneo e Independente Total:**
  - Suprime a interferência mútua entre mouses usando **Windows Raw Input API (`WM_INPUT`)** e um **Low-Level Hook (`WH_MOUSE_LL`)**.
  - Movimentos, cliques, **segurar e arrastar (Drag & Drop)** e rolagem da roda (scroll) de um mouse no Monitor X **não interferem nem interrompem** o mouse no Monitor Y.
  - As janelas clicadas pelo Mouse 1 no Monitor X são ativadas em primeiro plano (`SetForegroundWindow`), e as janelas clicadas pelo Mouse 2 no Monitor Y são ativadas independentemente sem roubo indevido de foco.
- **Ocultação do Ponteiro Padrão do Windows:**
  - Substitui temporariamente os cursores padrão brutos do Windows via `SetSystemCursor`, impedindo que a seta branca nativa do sistema fique por cima dos cursores do aplicativo. Restaura automaticamente os cursores ao pausar ou fechar o app (`SPI_SETCURSORS`).
- **Identificação Precisa por USB Hardware ID:**
  - Enumera e distingue os mouses pelo seu identificador USB único (`VID_xxxx&PID_yyyy` e Instance ID).
  - Identifica automaticamente fabricantes conhecidos (Logitech, Razer, Corsair, Microsoft, SteelSeries, etc.).
- **Delimitação de Monitores por Mouse:**
  - Defina em qual monitor cada mouse pode atuar (Ex: *Mouse 1 restrito ao Monitor 1*, *Mouse 2 restrito ao Monitor 2*, ou livre em *Todos os Monitores*).
  - Coordenadas são automaticamente limitadas (clamped) ao retângulo do monitor selecionado.
- **Design de Ponteiros Moderno, Limpo e Elegante:**
  - Visual minimalista com proporção áurea, sombra suave (drop shadow), bordas nítidas e pill badges estilizados.
  - **6 Formatos Modernos:** 
    1. *Seta Minimalista Sleek* (design moderno estilo macOS Sonoma / Windows 11 Fluent)
    2. *Seta Aerodinâmica Fluent* (entalhes aerodinâmicos suaves)
    3. *Seta Gamer Cyber* (linhas angulares futuristas)
    4. *Mira de Precisão Crosshair Pro* (retículo de alta acurácia com folga central)
    5. *Ponto Halo Neon Capsule* (marcador de foco circular minimalista)
    6. *Caneta Stylus Designer* (ponta de desenho e edição técnica)
  - **Paleta de Cores & Cores Customizadas:** Ciano Ártico (`#38BDF8`), Sunset Coral (`#FB923C`), Verde Esmeralda (`#10B981`), Rosa Neon (`#F43F5E`), Roxo Cyber (`#A855F7`), Dourado Âmbar (`#FBBF24`), Cinza Titânio (`#64748B`) e seletor de cores RGB livre.
  - **Efeito Glow / Aura Luminosa:** Círculo translúcido suave em volta do cursor para rápida localização em telas grandes ou 4K.
  - **Pill Badges de Identificação:** Exibe uma etiqueta limpa ("1", "2" ou "M1", "M2") com fundo slate escuro e borda coordenada.
  - **Slider de Tamanho:** Ajuste fino de 18px até 54px.
  - **Canvas com Pré-visualização Interativa:** Teste visual instantâneo do design na própria interface antes de aplicar.
- **Inicialização Automática com o Windows:**
  - Cria e remove com 1 clique o atalho nativo `.lnk` dentro da pasta `shell:startup` (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`).
- **Modo de Simulação / Testes:**
  - Permite demonstrar e testar o funcionamento dos dois cursores na tela mesmo se você só tiver 1 mouse conectado no momento.
- **Tecla de Pânico / Emergência (`F12`):**
  - Pausa e restaura o comportamento original do mouse instantaneamente com um toque de tecla.

---

## 🛠️ Arquitetura Técnica

O sistema foi concebido sem necessidade de drivers de kernel invasivos ou dependências externas pesadas:

```
[ Mouse USB 1 ] ---> Raw Input API (hDevice 1) ---> Motor DualPointer ---> Monitor 1 (pos1)
                                                           |
[ Mouse USB 2 ] ---> Raw Input API (hDevice 2) -----------+-------------> Monitor 2 (pos2)
                                                           |
                                                [ Low-Level Hook ]
                                              (Bloqueia blending do OS)
                                                           |
                                            [ Overlay Layered Window ]
                                           (Renderiza cursores GDI a 120 FPS)
```

1. **`core/devices.py`**: Interroga a lista de dispositivos brutos do Windows e o Registro (`HKLM\SYSTEM\CurrentControlSet\Services\mouhid\Enum`) para extrair os Hardware IDs (VID/PID) reais.
2. **`core/monitors.py`**: Consulta o subsistema de múltiplos monitores (`EnumDisplayMonitors`) e calcula limites virtuais.
3. **`core/engine.py`**: Thread de alta prioridade com janela de captura de eventos brutos, injeção de cliques via `SendInput` com flag `LLMHF_INJECTED`, e desenho de tela via janela transparente acelerada por hardware GDI.
4. **`core/startup.py`**: Integração com a interface COM `IShellLinkW` / `IPersistFile` para criação nativa de atalhos `.lnk` na pasta Inicializar.
5. **`gui/app.py`**: Interface moderna desenvolvida em Tkinter/TTK com suporte a High-DPI (telas 1080p, 1440p e 4K) e tema escuro Dark Slate.

---

## 🚀 Como Executar

### Opção 1: Executável Autônomo (.exe) — Recomendado
Basta dar um duplo clique diretamente no arquivo executável:
```
DualPointerPro.exe
```
*(Não requer ter Python instalado na máquina para rodar!)*

---

### Opção 2: Pelo Atalho Batch ou Código Fonte Python
1. Dê um duplo clique no arquivo:
   ```
   Iniciar_DualPointer.bat
   ```
   *Ou execute pelo terminal:*
   ```powershell
   python main.py
   ```

2. Na aba **🖱️ Mouses & Hardware (USB)**:
   - Selecione o **Mouse 1** e escolha o monitor correspondente (ex: Monitor 1).
   - Selecione o **Mouse 2** e escolha o outro monitor (ex: Monitor 2).
3. Na aba **🎨 Design dos Ponteiros**:
   - Escolha o formato, cor e tamanho do ponteiro de cada mouse.
4. Clique em **💾 Salvar Configurações**.
5. Pronto! Ambos os mouses funcionarão independentemente e simultaneamente.

---

## 👤 Sobre o Autor

- **Nome:** Caio Monteiro  
- **GitHub:** [@chacalbl4ck](https://github.com/chacalbl4ck)  
- **Repositório:** [https://github.com/chacalbl4ck](https://github.com/chacalbl4ck)  

Desenvolvido com excelência técnica para proporcionar produtividade máxima em estações multi-display e multi-dispositivo.

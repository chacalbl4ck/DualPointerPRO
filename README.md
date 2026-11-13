# 🖱️ DualPointer Pro

[![Versão](https://img.shields.io/badge/Vers%C3%A3o-1.1-38BDF8?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/chacalbl4ck)
[![Plataforma](https://img.shields.io/badge/Plataforma-Windows%2010%20%7C%2011%20x64-0078D6?style=for-the-badge&logo=windows)](https://github.com/chacalbl4ck)
[![Licença](https://img.shields.io/badge/Licen%C3%A7a-MIT-10B981?style=for-the-badge)](https://github.com/chacalbl4ck)
[![GitHub Actions](https://img.shields.io/badge/CI%2FCD-Automated%20Build%20%26%20Release-6366F1?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/chacalbl4ck)
[![Build & Release DualPointer Pro](https://github.com/chacalbl4ck/DualPointerPRO/actions/workflows/build.yml/badge.svg)](https://github.com/chacalbl4ck/DualPointerPRO/actions/workflows/build.yml)

> **Gerenciador Avançado de Múltiplos Mouses e Múltiplos Monitores Independentes para Windows**  
> Desenvolvido por **Caio Monteiro** ([@chacalbl4ck](https://github.com/chacalbl4ck))

---

## 📋 Sobre o Projeto

O **DualPointer Pro** é uma solução de alta performance em Python e Win32 API que permite conectar **dois mouses físicos** simultaneamente ao mesmo computador, separando totalmente seus movimentos, cliques, rolagens e delimitando os monitores onde cada um opera.

**Um mouse nunca interfere no movimento, no clique ou no foco do outro.**

Com identificação por **USB Hardware ID (VID & PID)**, personalização visual moderna dos cursores em alta resolução, renderização acelerada por GPU/GDI com latência zero e integração automática com a inicialização do Windows.

---

## ✨ Principais Funcionalidades (v1.1)

### 🖥️ Estações de Trabalho Independentes (Multi-Seat)
- Divide o computador em **Áreas de Trabalho Dedicadas**:
  - **Estação A (Mouse 1)**: Monitor(es) dedicado(s) e mouse USB exclusivo.
  - **Estação B (Mouse 2)**: Monitor(es) dedicado(s) e mouse USB exclusivo.
- **Isolamento Total de Cliques & Arraste Contínuo**:
  - Clicar, arrastar janelas (*Drag & Drop*) ou rolar a barra em uma tela **não cancela nem interrompe** a outra tela.
  - As janelas clicadas pelo Mouse 1 permanecem ativas na Estação A, e as janelas clicadas pelo Mouse 2 permanecem ativas na Estação B.
- **Telemetria de Janelas em Tempo Real**:
  - Identifica e exibe na interface gráfica qual aplicativo está em foco em cada estação.

### ⚡ Motor de Latência Ultrabaixa (4.000+ FPS)
- **Renderização por Dirty-Rectangles**:
  - Em vez de redesenhar a tela inteira, apenas as caixas delimitadoras de 64x64 pixels dos cursores são limpas e transferidas para o display em **0,01 ms**.
  - Atualização direta em resposta aos pacotes USB (`WM_INPUT`), eliminando a perda de quadros e o atraso do `WM_PAINT`.
- **Cache Completo de Objetos GDI**:
  - Canetas, pincéis, sombras suaves e fontes pré-alocados em memória; zero alocações ou fugas de handles por quadro.
- **Precisão Sub-pixel**:
  - Movimentos lentos e ajustes milimétricos de mira preservam coordenadas em ponto flutuante (`float`), eliminando qualquer sensação de "travamento" ao mirar em botões pequenos.
- **Sincronização Contínua de Hover**:
  - O cursor nativo do sistema acompanha continuamente o mouse em movimento. Botões, links, abas e menus acendem seus efeitos de *hover* instantaneamente.
- **Despacho Atômico de Cliques em Microssegundos**:
  - Disparo de cliques em lote único via `SendInput(n_events, ...)`. Consultas de janelas são feitas de forma assíncrona, reduzindo a latência do clique para menos de **0,5 ms**.

### 🛡️ Compatibilidade Total com Janelas de Sistema & UAC
- **Execução com Nível de Integridade Alta (Administrador)**:
  - O binário possui manifesto de elevação UAC embutido (`requireAdministrator`), garantindo que a camada de sobreposição fique visível e funcional mesmo sobre o **Gerenciador de Tarefas**, **Regedit**, **CMD/PowerShell elevado** e diálogos do Windows.
- **Re-asserção Automática de Topo (Z-Order)**:
  - Garante que janelas com configuração "Sempre visível" não fiquem na frente do cursor.
- **Mecanismo de Segurança (Fail-Safe)**:
  - Caso executado sem elevação, o motor detecta automaticamente a passagem sobre o Gerenciador de Tarefas e restaura o ponteiro nativo para nunca sumir.

### 🎨 Design de Ponteiros Moderno & Minimalista
- Visual de alta definição com proporção estética, sombra suave (*Drop Shadow*), bordas contrastantes e *Pill Badges* estilizados.
- **6 Formatos Modernos:**
  1. *Seta Minimalista Sleek* (estilo macOS / Windows 11 Fluent)
  2. *Seta Aerodinâmica Fluent* (entalhes aerodinâmicos suaves)
  3. *Seta Gamer Cyber* (ângulos agressivos e futuristas)
  4. *Mira de Precisão Crosshair Pro* (retículo tático com centro transparente)
  5. *Ponto Halo Neon Capsule* (marcador circular elegante)
  6. *Caneta Stylus Designer* (ponta de edição artística e técnica)
- **Paleta de Cores & Cores Personalizadas:** Cores vibrantes prontas + seletor RGB livre.
- **Aura Glow (Brilho Neon):** Círculo translúcido suave para rápida localização visual em telas grandes ou monitores 4K.
- **Pill Badges de Identificação:** Indicador elegante ("1" / "2" ou customizado).
- **Ajuste Fino de Escala:** Sliders de tamanho de 18px a 54px com pré-visualização interativa em tempo real.

### 🔌 Identificação por Hardware ID (USB)
- Enumera e distingue os mouses pelo seu identificador USB único (`VID_xxxx&PID_yyyy` e Instance ID).
- Suporte a mouses idênticos através de discriminação por porta física.
- Identificação automática de marcas (Logitech, Razer, Corsair, SteelSeries, etc.).

### 🚀 Inicialização com o Windows & Tecla de Emergência
- Ativação de inicialização automática com 1 clique (criação de atalho nativo `.lnk` na pasta `shell:startup`).
- **Tecla de Pânico (`F12`)**: Pausa ou retoma o motor instantaneamente com uma única tecla.

---

## 🛠️ Arquitetura Técnica

```
[ Mouse USB 1 ] ---> Raw Input API (hDevice 1) ---> Motor DualPointer ---> Estação A (Monitor 1)
                                                           |
[ Mouse USB 2 ] ---> Raw Input API (hDevice 2) -----------+-------------> Estação B (Monitor 2)
                                                           |
                                                [ Low-Level Hook ]
                                           (Cancela cruzamento do OS)
                                                           |
                                           [ Direct Overlay Window ]
                                        (Dirty-rect GDI a 4.000+ FPS)
```

| Módulo | Responsabilidade |
| :--- | :--- |
| **`core/devices.py`** | Enumeração de periféricos brutos via Raw Input e Registro do Windows (`VID`/`PID`). |
| **`core/monitors.py`** | Detecção dinâmica de múltiplos monitores (`EnumDisplayMonitors`) e cálculo de limites. |
| **`core/engine.py`** | Thread de altíssima prioridade, dirty-rect blitting, injeção atômica e hook de mouse. |
| **`core/startup.py`** | Integração com a interface COM `IShellLinkW` para gerenciamento do atalho de inicialização. |
| **`gui/app.py`** | Interface visual moderna com tema Dark Slate, suporte High-DPI e telemetria em tempo real. |
| **`gui/cursor_draw.py`** | Renderização vetorial dos cursores para a pré-visualização interativa. |

---

## 💻 Como Usar

### Opção 1: Executável Autônomo (.exe) — Recomendado
Basta baixar e executar o arquivo diretamente:
```powershell
.\DualPointerPro.exe
```
*(Não requer Python instalado na máquina).*

---

### Opção 2: A Partir do Código Fonte

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/chacalbl4ck/Mouse.git
   cd Mouse
   ```

2. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Inicie o aplicativo:**
   ```bash
   python main.py
   ```
   *Ou dê um duplo clique em `Iniciar_DualPointer.bat`.*

---

## ⚙️ Configuração Inicial Rápida

1. Abra o **DualPointer Pro**.
2. Na aba **🖱️ Mouses & Hardware**:
   - Escolha o **Mouse 1** e selecione o monitor correspondente (ex: *Monitor 1*).
   - Escolha o **Mouse 2** e selecione o outro monitor (ex: *Monitor 2*).
3. Na aba **🎨 Design dos Ponteiros**:
   - Ajuste o formato, a cor e o tamanho do ponteiro de cada mouse.
4. Clique em **💾 Salvar Configurações**.
5. Pronto! Cada mouse funcionará simultaneamente e de forma 100% isolada.

---

## 🤖 Integração Contínua & Releases Automáticas (CI/CD)

O repositório conta com um workflow automatizado no **GitHub Actions** ([.github/workflows/build.yml](.github/workflows/build.yml)) que:
- Compila o binário standalone `.exe` no ambiente Windows nativo a cada `git push`.
- Gera os checksums criptográficos **SHA-256**.
- Publica o executável automaticamente na aba **Releases** com a versão extraída de `config.json`.

---

## 👤 Autor & Créditos

- **Desenvolvedor:** Caio Monteiro  
- **GitHub:** [@chacalbl4ck](https://github.com/chacalbl4ck)  
- **Projeto:** [DualPointer Pro](https://github.com/chacalbl4ck)

Desenvolvido para máxima produtividade, ergonomia e precisão em estações de trabalho multi-display.

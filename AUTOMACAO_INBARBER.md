# Automação InBarber → WhatsApp — Especificação para Claude Code

Este documento descreve duas automações que o Luan (dono da Brax Barbearia) precisa
implementar, usando o painel web do InBarber (chat.inbarberapp.com ou o painel
administrativo equivalente, acessado via navegador).

Ler também `PROJETO_CONTEXTO.md` (contexto geral do negócio) antes de começar.

## Contexto do problema

O InBarber já gera a mensagem de lembrete de horário pronta, mas o envio é **manual**:
o Luan precisa entrar no painel todos os dias e clicar num ícone de sino, cliente por
cliente, para disparar cada lembrete. Ele esquece de fazer isso com frequência.

Não existe API pública documentada do InBarber para integração de terceiros — a
automação precisa ser feita via **automação de navegador** (ex: Playwright ou
Selenium), controlando o painel web como um usuário faria.

## Tarefa 1 — Lembretes automáticos diários

**Objetivo:** todo dia, num horário fixo (sugestão: 8h da manhã), abrir o painel do
InBarber, localizar os agendamentos do dia, e clicar automaticamente no botão/ícone de
envio de lembrete ("sino") para cada cliente agendado.

**Passos esperados do script:**
1. Fazer login no painel web do InBarber (credenciais via variáveis de ambiente
   locais — nunca hardcoded no código, nunca compartilhadas em chat)
2. Navegar até a lista/agenda do dia atual
3. Para cada agendamento do dia, localizar e clicar no botão de enviar lembrete
4. Registrar um log simples (cliente, horário, sucesso/falha) para o Luan conseguir
   auditar depois se precisar
5. Rodar automaticamente via agendador (cron no Linux/Mac, Task Scheduler no Windows,
   ou um serviço de cron na nuvem tipo GitHub Actions/Railway/Render, caso o
   computador do Luan não fique ligado o dia todo)

**Observação:** o Luan confirmou que acessa o InBarber pelo navegador do computador
(painel web), então a automação de navegador é viável.

## Tarefa 2 — Reengajamento de clientes inativos ("busca-clientes")

**Objetivo:** identificar clientes que não agendam há um tempo (ex: 30, 45 ou 60 dias
— perguntar ao Luan qual prazo prefere) e gerar uma forma de contatá-los via WhatsApp
incentivando um novo agendamento.

**Passos esperados do script:**
1. Login no painel (reaproveitar sessão/lógica da Tarefa 1)
2. Navegar até a lista de clientes, que exibe a data do último atendimento de cada um
   (o Luan confirmou que essa informação existe no painel)
3. Filtrar clientes cuja última visita é mais antiga que o limite definido
4. Para cada cliente inativo, gerar uma mensagem de reengajamento personalizada
   (nome do cliente + tempo sem aparecer + call-to-action) e um link `wa.me` pronto
   com a mensagem pré-preenchida (formato: `https://wa.me/55DDDNUMERO?text=...`)
5. **Importante:** verificar se o InBarber tem algum recurso nativo de mensagem em
   massa para clientes inativos antes de decidir a abordagem final. Se não tiver,
   a saída mais simples e seguindo os Termos de Uso do WhatsApp é gerar uma lista de
   links prontos (um por cliente) para o Luan revisar e clicar manualmente — evita
   qualquer risco de banimento do número por automação não-oficial do WhatsApp em si
   (a automação aqui é só no lado do InBarber/geração de mensagem, o envio final
   pelo WhatsApp continua sendo uma ação manual de clique, o que é seguro).

## Tarefa 3 — Agradecimento + pedido de avaliação pós-atendimento

**Objetivo:** depois que um cliente é atendido (agendamento marcado como concluído no
InBarber, ou simplesmente após o horário do agendamento já ter passado no dia), gerar
uma mensagem de agradecimento pedindo avaliação no Google.

**Mensagem aprovada pelo Luan:**
```
Olá [Nome]! Foi um prazer ter você aqui na Brax Barbearia hoje 🙌 Se puder, deixa uma
avaliação rápida pra gente — ajuda muito: https://g.page/r/CV1J1wlkleRqEAE/review
Até a próxima!
```

**Passos esperados do script:**
1. Login no painel (reaproveitar lógica da Tarefa 1)
2. Ao final do dia (sugestão: rodar por volta das 20h30-21h, após o fechamento),
   localizar todos os agendamentos do dia que foram concluídos/atendidos
3. Para cada cliente atendido, gerar a mensagem acima com o nome substituído, e um
   link `wa.me` pronto: `https://wa.me/55DDDNUMERO?text=<mensagem codificada>`
4. Mesma lógica de segurança da Tarefa 2: gerar os links prontos para o Luan clicar
   e confirmar o envio manualmente, em vez de automatizar o envio direto pelo
   WhatsApp — evita risco de banimento do número por automação não-oficial
5. Se o InBarber não distinguir "concluído" de "agendado" de forma clara na interface,
   uma alternativa simples é rodar isso só para agendamentos cujo horário já passou
   no dia corrente (assumindo que o cliente compareceu, já que não há indicação de
   cancelamento)

**Observação:** essa tarefa é a mais parecida estruturalmente com a Tarefa 1 (mesmo
tipo de varredura da agenda do dia), então pode reaproveitar boa parte do código de
login e navegação já construído para ela.


- **Nunca automatizar o envio direto de mensagens pelo WhatsApp Web/App** (ex: via
  bibliotecas não-oficiais tipo whatsapp-web.js/Baileys) sem que o Luan esteja
  ciente do risco de banimento do número por violar os Termos de Uso da Meta. Se ele
  quiser esse nível de automação completa no futuro, a via seria a API oficial paga
  (BSP + Meta) — já discutido com ele anteriormente nesta conversa.
- Credenciais do InBarber devem ficar em arquivo `.env` local, nunca commitadas no
  Git nem compartilhadas em chat.
- Perguntar ao Luan qual o prazo de inatividade ideal para a Tarefa 2 antes de
  implementar (sugestão inicial: 45 dias).
- Ao inspecionar o painel do InBarber para identificar seletores de botões, fazer
  isso interativamente (abrir o navegador, localizar os elementos reais) já que a
  estrutura exata da página não está documentada aqui.

[PROJETO_CONTEXTO.md](https://github.com/user-attachments/files/31524248/PROJETO_CONTEXTO.md)
# Brax Barbearia — Contexto do Projeto

Este arquivo resume o projeto para quem for dar continuidade (ex: Claude Code).
O site foi construído em outra conversa (Claude.ai) e migrado para este repositório.

## Sobre o negócio
- **Nome:** Brax Barbearia
- **Endereço:** R. Clélia, 151 — Rio Branco, Belo Horizonte - MG, 31530-530
- **WhatsApp:** (31) 99291-6354 → usado como `https://wa.me/5531992916354`
- **Agendamento:** https://chat.inbarberapp.com/Braxbarbearia
- **Instagram:** @braxbarbearia
- **Horário:** Seg-Sáb 08:00-20:00, Domingo 08:00-13:00
- **Domínio:** braxbarbearia.com.br (registrado no registro.br, DNS aponta pro Netlify)
- **Google Meu Negócio:** 5,0⭐ com 58 avaliações (nome antigo no Google: "Barber Shop World")

## Stack técnica
- Site estático simples: HTML + CSS + JS puro (sem framework, sem build step)
- Hospedagem: Netlify, conectado a este repositório GitHub (deploy automático a cada commit na branch `main`)
- **Diretório de publicação no Netlify: `Site Brax`** (os arquivos do site ficam dentro dessa pasta, não na raiz do repo — isso foi assim porque o upload inicial pelo GitHub web criou essa subpasta sem querer, e ficou configurado assim no Netlify)

## Estrutura de arquivos (dentro de `Site Brax/`)
```
index.html          → página principal
privacidade.html     → política de privacidade (LGPD)
sitemap.xml
robots.txt
assets/
  styles.css         → TODO o CSS do site (compartilhado entre index.html e privacidade.html)
  logo.png           → logo oficial (3D dourado, fundo transparente)
  emblem.png         → só o brasão/escudo recortado da logo (sem o texto "BRAX BARBEARIA")
  favicon.ico, favicon-*.png, apple-touch-icon.png
  og-image.jpg       → imagem de prévia para compartilhamento (WhatsApp/redes sociais)
  gallery-1.jpg até gallery-6.jpg  → fotos reais de cortes/ambiente da barbearia
  [produtos].png     → fotos de produtos com fundo removido (transparente), ex: pasta-brilho.png, serum-forcemen.png, minoxidil-frasco.png, etc.
```

## Identidade visual (design tokens)
- **Cores:** fundo quase preto (`#0a0a0b`), dourado (`#c9a24b` / `#e6c675` mais claro), texto marfim (`#f3efe4`), cinza muted (`#9a968c`)
- **Fontes:** 'Cormorant SC' (títulos/serifada elegante), 'Manrope' (corpo do texto), 'Space Mono' (labels técnicos, preços, "eyebrows")
- **Estilo geral:** clássico/heráldico (brasão, coroa) combinado com minimalista/moderno — dourado sobre preto, bastante espaço em branco, hairlines douradas como divisores entre seções
- Motivo repetido como divisor entre seções: um pequeno losango dourado (SVG) entre duas linhas horizontais finas

## Funcionalidades já implementadas
1. **Hero** com logo, tagline "Viva sua experiência na Brax. Agende em segundos.", botões de Agendar e WhatsApp
2. **Faixa de promoção**: primeiro corte por R$30 (só novos clientes)
3. **Seção "Nossa História"** com o texto institucional da marca
4. **Serviços** — tabela de preços em 3 categorias (Avulsos, Estética & Tratamentos, Assinaturas)
5. **Galeria** — 6 fotos reais de cortes/ambiente
6. **Produtos** — 13 produtos com foto (fundo removido), descrição, preço e botão "Reservar" (abre WhatsApp com mensagem pré-preenchida citando o produto). Categorias: Styling & Finalização, Crescimento Capilar, Corporal. Produtos da marca Kannep foram removidos a pedido do dono (não trabalha mais com a marca)
7. **Avaliações** — 4 depoimentos reais copiados do Google, com nota 5,0⭐/58 avaliações
8. **Localização** — mapa embutido do Google Maps + endereço + botão "Como chegar"
9. **Horários** — com destaque automático (JS) do dia atual e indicador "aberto/fechado agora"
10. **FAQ** — 6 perguntas em formato acordeão (`<details>/<summary>`)
11. **Footer** com links e política de privacidade
12. **SEO**: dados estruturados JSON-LD (schema.org HairSalon), sitemap.xml, robots.txt, meta tags Open Graph/Twitter Card, canonical
13. **Google Analytics** (GA4, measurement ID `G-MPMCFSD4QN`) com rastreamento de cliques customizado em: WhatsApp, Agendar, Como chegar, Instagram, Reservar (por produto)
14. **Mobile**: botões fixos (sticky) de WhatsApp + Agendar no rodapé em telas pequenas; ícone do Instagram sempre visível no cabeçalho (não escondido no menu mobile)

## Pendências conhecidas
- **Seção "Time/Barbeiros"**: ainda não implementada — o dono (Luan) vai tirar fotos profissionais da equipe e mandar depois
- Falta cadastrar/vincular o Google Meu Negócio mais formalmente ao Search Console (verificação de domínio via DNS já foi feita e funcionou)

## Erros/bugs já corrigidos (não reintroduzir)
- **Bug de especificidade CSS**: a regra `@media (max-width:760px){ .nav-links{display:none;} }` não funcionava porque a regra base `nav .nav-links{display:flex}` tinha especificidade maior. Corrigido usando `nav .nav-links{display:none}` dentro do media query. Cuidado ao editar regras de media query — sempre confirmar que a especificidade do seletor dentro do `@media` é igual ou maior que a regra que está sobrescrevendo.
- Instagram estava dentro de `.nav-links` (escondido no mobile) — foi movido para `.nav-actions`, um contêiner sempre visível.

## Preferências do cliente (Luan)
- Prefere respostas em português (Brasil)
- Já passou por um processo de configuração manual longo no Netlify/registro.br/Search Console — prefere passo a passo bem detalhado e confirmação por print quando mexe em painéis externos
- É bem receptivo a sugestões proativas de melhoria (SEO, Analytics, LGPD, FAQ foram todas sugestões aceitas)
- Sensível a direitos autorais de imagens — já recusou usar fotos oficiais de fabricante sem autorização/fonte própria (preferiu tirar fotos próprias dos produtos)

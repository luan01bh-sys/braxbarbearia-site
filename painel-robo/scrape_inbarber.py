"""
Lê os agendamentos do dia no painel do InBarber (schedule.inbarberapp.com).

O InBarber não tem API pública, então isto é automação de navegador (Playwright):
faz login e, para CADA profissional (o dono + colaboradores), abre a agenda daquele
profissional e lê nome, horário e telefone de cada agendamento. O telefone vem do
link de WhatsApp que o botão de "sino" monta — o script clica no sino, intercepta o
link (sem abrir o WhatsApp) e lê o número.

Cada agendamento sai marcado com `profissional` = primeiro nome de quem vai atender.
"""

import os
import re
import sys
import json
import datetime as dt
from pathlib import Path

from playwright.sync_api import sync_playwright

PAINEL_URL = "https://schedule.inbarberapp.com/details"
LOGS_DIR = Path(__file__).parent / "logs"

WHATS_PATTERNS = ["**/api.whatsapp.com/**", "**/wa.me/**", "**/web.whatsapp.com/**"]

RE_HORARIO = re.compile(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})")
RE_PHONE = re.compile(r"[?&]phone=(\d+)")

# nomes de card que NÃO são cliente (bloqueio de agenda / almoço)
NAO_CLIENTE = ("", "fechado", "horário fechado", "horario fechado")


def _log(msg: str) -> None:
    print(f"[scrape] {msg}", flush=True)


def _fazer_login(page, email: str, senha: str) -> None:
    page.goto(PAINEL_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)

    if page.query_selector(".vuecal__cell--today, .vuecal__event"):
        _log("Sessão já autenticada.")
        return

    _log("Tela de login detectada, autenticando...")
    entrar = page.query_selector("text=ENTRAR")
    if entrar:
        entrar.click()
        page.wait_for_timeout(1500)

    email_input = (
        page.query_selector("input[type='email']")
        or page.query_selector("input[placeholder*='mail' i]")
        or page.query_selector("input[name*='mail' i]")
    )
    senha_input = (
        page.query_selector("input[type='password']")
        or page.query_selector("input[placeholder*='senha' i]")
    )
    if not email_input or not senha_input:
        raise RuntimeError("Não encontrei os campos de login no InBarber.")

    email_input.fill(email)
    senha_input.fill(senha)

    botao = (
        page.query_selector("button:has-text('ENVIAR')")
        or page.query_selector("text=ENVIAR")
        or page.query_selector("button[type='submit']")
    )
    if not botao:
        raise RuntimeError("Não encontrei o botão ENVIAR do login.")
    botao.click()

    page.wait_for_selector(".vuecal__cell--today, .vuecal__event", timeout=30000)
    page.wait_for_timeout(2000)
    _log("Login OK.")


def _garantir_dia_de_hoje(page) -> None:
    selecionado_e_hoje = page.evaluate(
        """() => {
            const sel = document.querySelector('.vuecal__cell--selected');
            return !!(sel && sel.classList.contains('vuecal__cell--today'));
        }"""
    )
    if not selecionado_e_hoje:
        hoje = page.query_selector(".vuecal__cell--today")
        if hoje:
            hoje.click()
            page.wait_for_timeout(1500)


def _abrir_seletor_agenda(page) -> bool:
    """Abre o modal 'Escolha qual agenda'. Idempotente. False se não há seletor."""
    if page.query_selector("label.item-radio"):
        return True
    trigger = page.query_selector(".select-user")
    if not trigger:
        return False
    trigger.click()
    try:
        page.wait_for_selector("label.item-radio", timeout=4000)
        return True
    except Exception:
        return False


def _listar_profissionais(page) -> list[dict]:
    return page.evaluate(
        """() => [...document.querySelectorAll('label.item-radio')].map(l => ({
            radioId: l.getAttribute('for'),
            nome: (l.querySelector('.collab-name')?.textContent || '').trim(),
        }))"""
    )


def _selecionar_profissional(page, radio_id: str) -> None:
    page.click(f"label[for='{radio_id}']")
    page.wait_for_timeout(3000)  # a agenda recarrega para o profissional escolhido
    _garantir_dia_de_hoje(page)
    page.wait_for_timeout(1000)


def _ler_cards(page) -> list[dict]:
    dados = page.evaluate(
        """() => {
            const eventos = [...document.querySelectorAll('.vuecal__event')];
            return eventos.map((ev, i) => {
                const sv = ev.querySelector('.service-value');
                const badge = sv ? sv.querySelector('.badge') : null;
                return {
                    indice: i,
                    isLunch: ev.classList.contains('lunch'),
                    temSino: !!ev.querySelector('#edit, .icon-title.pr-2'),
                    horarioTexto: (ev.querySelector('p.text-left')?.textContent || '').trim(),
                    nome: (ev.querySelector('.name')?.textContent || '').trim(),
                    servico: (ev.querySelector('.item')?.textContent || '').trim(),
                    // pagamento lançado = tem selo (PIX / CRÉD. / DIN. / ASSIN.) no valor
                    pago: !!badge,
                    formaPgto: badge ? badge.textContent.trim() : null,
                    valor: sv ? (sv.querySelector('span:last-child')?.textContent || '').trim() : '',
                };
            });
        }"""
    )

    cards = []
    for d in dados:
        if d["isLunch"] or not d["temSino"]:
            continue
        if d["nome"].strip().lower() in NAO_CLIENTE:
            continue
        m = RE_HORARIO.search(d["horarioTexto"])
        if not m:
            _log(f"Ignorando card sem horário legível: {d!r}")
            continue
        cards.append(
            {
                "indice": d["indice"],
                "nome": d["nome"],
                "horario": m.group(1),
                "servico": d["servico"],
                "telefone": None,
                "profissional": None,
                "pago": d.get("pago", False),
                "forma_pgto": d.get("formaPgto"),
                "valor": d.get("valor", ""),
            }
        )
    return cards


def _capturar_telefone(page, indice: int) -> str | None:
    capturado = {"url": None}

    def handler(route):
        capturado["url"] = route.request.url
        route.abort()

    for pat in WHATS_PATTERNS:
        page.context.route(pat, handler)

    try:
        eventos = page.query_selector_all(".vuecal__event")
        if indice >= len(eventos):
            return None
        sino = eventos[indice].query_selector("#edit, .icon-title.pr-2")
        if not sino:
            return None
        sino.scroll_into_view_if_needed()
        sino.click()
        page.wait_for_timeout(1200)

        url = capturado["url"]

        if "schedule.inbarberapp.com" not in page.url:
            try:
                page.go_back(wait_until="domcontentloaded")
                page.wait_for_timeout(1500)
            except Exception:
                page.goto(PAINEL_URL, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)

        if not url:
            return None
        m = RE_PHONE.search(url)
        return m.group(1) if m else None
    finally:
        for pat in WHATS_PATTERNS:
            try:
                page.context.unroute(pat, handler)
            except Exception:
                pass


def _raspar_agenda_atual(page, primeiro_nome: str) -> list[dict]:
    cards = _ler_cards(page)
    _log(f"  {primeiro_nome or '(agenda atual)'}: {len(cards)} agendamento(s).")
    for card in cards:
        card["telefone"] = _capturar_telefone(page, card["indice"])
        card["profissional"] = primeiro_nome
        _log(
            f"    {card['horario']} - {card['nome']} - "
            f"{card['telefone'] or 'SEM TELEFONE'}"
        )
    return cards


def ler_agendamentos_de_hoje(email: str, senha: str, headless: bool = True) -> list[dict]:
    """Retorna [{nome, horario, servico, telefone, profissional}] de HOJE, de todos os profissionais."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(locale="pt-BR")
        page = context.new_page()
        try:
            _fazer_login(page, email, senha)
            _garantir_dia_de_hoje(page)
            page.wait_for_timeout(1500)

            tem_seletor = _abrir_seletor_agenda(page)
            if not tem_seletor:
                _log("Sem seletor de profissionais — raspando só a agenda atual.")
                return _raspar_agenda_atual(page, "")

            profissionais = _listar_profissionais(page)
            _log(
                f"{len(profissionais)} profissional(is): "
                + ", ".join(p["nome"] for p in profissionais)
            )

            todos: list[dict] = []
            for prof in profissionais:
                primeiro_nome = (prof["nome"].split() or [""])[0]
                _abrir_seletor_agenda(page)
                _selecionar_profissional(page, prof["radioId"])
                todos.extend(_raspar_agenda_atual(page, primeiro_nome))
            return todos
        finally:
            context.close()
            browser.close()


REMARKETING_URL = "https://schedule.inbarberapp.com/menu/client/remarketing"
_MESES = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
          "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
RE_ULTVISITA = re.compile(r"([A-Za-z]{3})\s+(\d{1,2}),\s*(\d{4})")


def _parse_ultima_visita(texto: str):
    """'Bruno Afonso - Jul 30, 2026' -> (nome, date(2026,7,30))."""
    m = RE_ULTVISITA.search(texto or "")
    data = None
    if m:
        mes = _MESES.get(m.group(1).lower())
        if mes:
            try:
                data = dt.date(int(m.group(3)), mes, int(m.group(2)))
            except ValueError:
                data = None
    nome = texto
    if m:
        nome = texto[: m.start()].rstrip(" -").strip()
    return nome.strip(), data


def ler_clientes_inativos(email: str, senha: str, dias_min: int = 20,
                          headless: bool = True) -> list[dict]:
    """
    Lê a tela 'Últimas Visitas' (/menu/client/remarketing) filtrando por
    'não comparecem há mais de <dias_min> dias'. Retorna
    [{nome, telefone, ultima_visita (date|None), profissional}].
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(locale="pt-BR")
        page = context.new_page()
        try:
            _fazer_login(page, email, senha)
            page.goto(REMARKETING_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            valores = [o for o in ("60", "40", "30", "20", "15", "10") if int(o) >= dias_min]
            alvo = str(min(int(v) for v in valores)) if valores else str(dias_min)
            try:
                page.wait_for_selector("select", timeout=15000)
                page.select_option("select", alvo)
                page.wait_for_timeout(3500)
            except Exception as e:
                _log(f"Não consegui setar o filtro ({e}). Seguindo com o que estiver na tela.")

            # rola a pagina pra carregar mais linhas (lista lazy-load)
            try:
                prev = -1
                for _ in range(12):
                    n = page.evaluate("document.querySelectorAll('.item-list').length")
                    if n == prev:
                        break
                    prev = n
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(1200)
            except Exception:
                pass

            dados = page.evaluate(
                """() => [...document.querySelectorAll('.item-list')].map(el => {
                    const ps = [...el.querySelectorAll('p')].map(p => p.textContent.trim());
                    const nome = ps[0] || '';
                    // telefone = o <p> (fora o 'Atendido por') com >= 10 digitos
                    const tel = ps
                      .filter(t => !/Atendido/i.test(t))
                      .map(t => t.replace(/\\D/g, ''))
                      .find(d => d.length >= 10) || '';
                    const prof = (ps.find(t => /Atendido por/i.test(t)) || '').replace(/Atendido por:?\\s*/i, '');
                    return { nome, tel, prof };
                })"""
            )

            out = []
            for d in dados:
                nome, ultv = _parse_ultima_visita(d["nome"])
                tel = re.sub(r"\D", "", d.get("tel", ""))
                if not nome or not tel:
                    continue
                out.append({
                    "nome": nome,
                    "telefone": tel,
                    "ultima_visita": ultv.isoformat() if ultv else None,
                    "profissional": (d.get("prof") or "").strip(),
                })
            _log(f"{len(out)} clientes inativos lidos (filtro: +{alvo} dias).")
            return out
        finally:
            context.close()
            browser.close()


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()
    email = os.environ.get("INBARBER_EMAIL")
    senha = os.environ.get("INBARBER_PASSWORD")
    if not email or not senha:
        _log("Defina INBARBER_EMAIL e INBARBER_PASSWORD (no .env ou nos Secrets).")
        sys.exit(2)

    headless = os.environ.get("HEADLESS", "1") != "0"
    agendamentos = ler_agendamentos_de_hoje(email, senha, headless=headless)

    LOGS_DIR.mkdir(exist_ok=True)
    hoje = dt.date.today().isoformat()
    destino = LOGS_DIR / f"agendamentos_{hoje}.json"
    destino.write_text(
        json.dumps(agendamentos, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _log(f"Salvo em {destino}")
    print(json.dumps(agendamentos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

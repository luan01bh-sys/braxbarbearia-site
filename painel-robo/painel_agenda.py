"""
Painel de agenda dos tablets (braxbarbearia.com.br/painel/).

Lê a agenda de HOJE de cada profissional no InBarber e grava `saida/agenda.json`
CRIPTOGRAFADO (AES-256-GCM). A chave fica só no secret PAINEL_KEY e no link dos
tablets (depois do #, que nunca vai para servidor nenhum). O arquivo é publicado no
branch `painel-dados` deste repositório público — sem a chave, ninguém consegue ler.

Privacidade: só primeiro nome + inicial do sobrenome, horário e serviço. Sem telefone.
Este script não imprime nome de cliente no log (o log das Actions é público).
"""

import base64
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from playwright.sync_api import sync_playwright

import scrape_inbarber as ib

TZ = ZoneInfo("America/Sao_Paulo")
SAIDA = Path(__file__).parent / "saida" / "agenda.json"
RE_FAIXA = re.compile(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})")


def log(msg: str) -> None:
    print(f"[painel] {msg}", flush=True)


def nome_curto(nome: str) -> str:
    partes = [p for p in re.split(r"\s+", (nome or "").strip()) if p]
    if not partes:
        return "Cliente"
    primeiro = partes[0].capitalize()
    if len(partes) > 1:
        return f"{primeiro} {partes[-1][0].upper()}."
    return primeiro


def ler_cards(page) -> list[dict]:
    dados = page.evaluate(
        """() => [...document.querySelectorAll('.vuecal__event')].map(ev => {
            const sv = ev.querySelector('.service-value');
            return {
                isLunch: ev.classList.contains('lunch'),
                temSino: !!ev.querySelector('#edit, .icon-title.pr-2'),
                faixa: (ev.querySelector('p.text-left')?.textContent || '').trim(),
                nome: (ev.querySelector('.name')?.textContent || '').trim(),
                servico: (ev.querySelector('.item')?.textContent || '').trim(),
                pago: !!(sv && sv.querySelector('.badge')),
            };
        })"""
    )
    saida = []
    for d in dados:
        if d["isLunch"] or not d["temSino"]:
            continue
        if d["nome"].strip().lower() in ib.NAO_CLIENTE:
            continue
        m = RE_FAIXA.search(d["faixa"])
        if not m:
            continue
        saida.append({
            "inicio": m.group(1).zfill(5),
            "fim": m.group(2).zfill(5),
            "cliente": nome_curto(d["nome"]),
            "servico": re.sub(r"\s+", " ", d["servico"]).strip(),
            "pago": bool(d["pago"]),
        })
    saida.sort(key=lambda x: x["inicio"])
    return saida


def ler_agenda(email: str, senha: str) -> dict:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=os.environ.get("HEADLESS", "1") != "0")
        context = browser.new_context(locale="pt-BR")
        page = context.new_page()
        try:
            ib._fazer_login(page, email, senha)
            ib._garantir_dia_de_hoje(page)
            page.wait_for_timeout(1500)
            agenda: dict[str, list] = {}
            if not ib._abrir_seletor_agenda(page):
                agenda["Agenda"] = ler_cards(page)
                return agenda
            profissionais = ib._listar_profissionais(page)
            for prof in profissionais:
                primeiro = (prof["nome"].split() or ["Profissional"])[0].capitalize()
                ib._abrir_seletor_agenda(page)
                ib._selecionar_profissional(page, prof["radioId"])
                agenda[primeiro] = ler_cards(page)
                log(f"{primeiro}: {len(agenda[primeiro])} agendamento(s)")
            return agenda
        finally:
            context.close()
            browser.close()


def cifrar(dados: dict, chave_b64: str) -> dict:
    chave = base64.urlsafe_b64decode(chave_b64 + "=" * (-len(chave_b64) % 4))
    if len(chave) != 32:
        raise SystemExit("PAINEL_KEY precisa ter 32 bytes (base64url).")
    iv = os.urandom(12)
    ct = AESGCM(chave).encrypt(iv, json.dumps(dados, ensure_ascii=False).encode(), None)
    b64 = lambda b: base64.b64encode(b).decode()
    return {"v": 1, "iv": b64(iv), "ct": b64(ct)}


def main() -> int:
    email = os.environ.get("INBARBER_EMAIL", "").strip()
    senha = os.environ.get("INBARBER_PASSWORD", "").strip()
    chave = os.environ.get("PAINEL_KEY", "").strip()
    if not (email and senha and chave):
        log("Faltam secrets: INBARBER_EMAIL, INBARBER_PASSWORD e/ou PAINEL_KEY. Pulando.")
        return 0
    agora = dt.datetime.now(TZ)
    agenda = ler_agenda(email, senha)
    dados = {
        "data": agora.strftime("%Y-%m-%d"),
        "atualizado": agora.isoformat(timespec="seconds"),
        "profissionais": agenda,
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(cifrar(dados, chave)), encoding="utf-8")
    log(f"Agenda gravada ({sum(len(v) for v in agenda.values())} agendamentos no total).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

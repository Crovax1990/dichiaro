"""Dichiaro — Il tuo 730 sotto controllo."""

import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy.orm import Session

from backend.models import (
    Persona, Dichiarazione, QuadroC_Lavoro, QuadroB_Fabbricati,
    QuadroE_Oneri, Risultato, create_engine_session,
)
from backend.parser.extractor import parse_730
from backend.parser.importer import import_pdf_to_db
from datetime import date

st.set_page_config(
    page_title="Dichiaro",
    page_icon="🏛️",
    layout="wide",
)

DB_PATH = Path("backend/analyzer.db")


def get_session() -> Session:
    engine, SessionLocal = create_engine_session(str(DB_PATH))
    return SessionLocal()


UTILIZZO_MAP = {
    1: "Abitazione principale",
    2: "Pertinenza abitaz. princ.",
    3: "Abitazione a disposizione",
    5: "Abitazione principale (ex)",
    9: "Altro immobile",
    10: "Immobile locato (libero m.)",
    11: "Immobile locato (canone conc.)",
}


def _oneri_category(code: str, desc: str | None) -> str:
    """Group Quadro E codes into human-readable categories."""
    desc = (desc or "").lower()
    mapping = {
        "E1": "Spese sanitarie",
        "E2": "Spese sanitarie (disabilità)",
        "E3": "Spese sanitarie (patologie esenti)",
        "E7": "Interessi mutuo prima casa",
        "E8": "Assicurazioni vita/infortuni",
        "E9": "Spese istruzione",
        "E10": "Spese istruzione",
        "E11": "Spese istruzione",
        "E12": "Spese universitarie",
        "E13": "Spese universitarie",
        "E14": "Spese affitto studenti",
        "E15": "Spese asili nido",
        "E16": "Spese attività sportive",
        "E17": "Spese cani guida",
        "E18": "Spese trasporto pubblico",
        "E19": "Spese badanti",
        "E20": "Spese interpretariato",
        "E21": "Spese farmaci",
        "E22": "Spese dispositivi medici",
        "E31": "Erogazioni liberali ONLUS",
        "E33": "Somme restituite al sostituto",
        "E34": "Contributi previdenziali",
        "E35": "Contributi previdenziali",
    }
    if code in mapping:
        return mapping[code]
    # Recupero edilizio / risparmio energetico
    if code.startswith("E4"):
        if "energ" in desc or code in ("E61", "E62"):
            return "Risparmio energetico"
        return "Recupero edilizio"
    # Generic fallback
    if "sanitar" in desc:
        return "Spese sanitarie"
    if "mutuo" in desc or "interessi" in desc:
        return "Interessi mutuo"
    if "ediliz" in desc or "ristruttur" in desc:
        return "Recupero edilizio"
    if "energ" in desc:
        return "Risparmio energetico"
    if "istruz" in desc or "universit" in desc:
        return "Spese istruzione"
    return f"Altro ({code})"


def _pl_preview(pl: dict, suffix: str) -> str:
    for k, v in pl.items():
        if k.endswith(suffix) and isinstance(v, dict):
            val = v.get("valore")
            return f"€ {val:,.0f}" if isinstance(val, (int, float)) else str(val or "—")
    return "—"


# ── Sidebar ──────────────────────────────────────────────────────────

st.sidebar.title("🏛️ Dichiaro")

session = get_session()

# Persone dropdown
persone = session.query(Persona).all()
persona_map = {f"{p.cognome} {p.nome} ({p.codice_fiscale})": p for p in persone}
persona_names = list(persona_map.keys()) + ["＋ Nuova persona"]

selected_persona_name = st.sidebar.selectbox("Persona", persona_names)

if selected_persona_name == "＋ Nuova persona":
    with st.sidebar.expander("Nuova persona", expanded=True):
        cf = st.text_input("Codice Fiscale", max_chars=16)
        nome = st.text_input("Nome")
        cognome = st.text_input("Cognome")
        if st.button("Crea persona") and cf and nome and cognome:
            existing = session.query(Persona).filter_by(codice_fiscale=cf.upper()).first()
            if existing:
                st.error("Persona già esistente")
            else:
                p = Persona(codice_fiscale=cf.upper(), nome=nome.upper(), cognome=cognome.upper())
                session.add(p)
                session.commit()
                st.success("Persona creata")
                st.rerun()
    selected_persona = None
else:
    selected_persona = persona_map[selected_persona_name]

# Anno dropdown
anni_disponibili = [d.anno_fiscale for d in session.query(Dichiarazione.anno_fiscale).distinct().order_by(Dichiarazione.anno_fiscale)]
anno = st.sidebar.selectbox("Anno fiscale", anni_disponibili + [date.today().year] if anni_disponibili else [date.today().year], index=len(anni_disponibili)-1 if anni_disponibili else 0)

# Navigation
page = st.sidebar.radio("Sezione", ["📤 Importa PDF", "📊 Riepilogo Annuale", "📈 Trend", "🔔 Alert"])

# ── Import PDF ───────────────────────────────────────────────────────

if page == "📤 Importa PDF":
    st.title("Importa 730 da PDF")
    st.caption("Carica uno o più PDF — anno e persona vengono rilevati automaticamente.")

    uploaded_files = st.file_uploader(
        "Carica i PDF del 730/RedditiPF", type=["pdf"], accept_multiple_files=True
    )

    if uploaded_files:
        st.info(f"{len(uploaded_files)} file{'s' if len(uploaded_files) > 1 else ''} caricato{'i' if len(uploaded_files) > 1 else ''}")

        if st.button("🔍 Analizza tutti", type="primary"):
            previews = []
            temp_paths = []

            with st.spinner(f"Analisi di {len(uploaded_files)} file in corso..."):
                for uf in uploaded_files:
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        tmp.write(uf.read())
                        tmp_path = tmp.name
                    temp_paths.append(tmp_path)

                    try:
                        data = parse_730(tmp_path)
                        meta = data.get("metadata", {})
                        pl = data.get("prospetto_liquidazione", {})
                        val = data.get("validazione", {})

                        cf = meta.get("codice_fiscale", "—")
                        existing = session.query(Persona).filter_by(codice_fiscale=cf).first()

                        previews.append({
                            "filename": uf.name,
                            "path": tmp_path,
                            "data": data,
                            "anno": meta.get("anno", "—"),
                            "cf": cf,
                            "nome": meta.get("nome", "—"),
                            "cognome": meta.get("cognome", "—"),
                            "reddito": _pl_preview(pl, "11_col_1"),
                            "imposta_netta": _pl_preview(pl, "50_col_1"),
                            "differenza": _pl_preview(pl, "60_col_1"),
                            "validazione_ok": val.get("ok"),
                            "persona_esistente": existing is not None,
                        })
                    except Exception as e:
                        previews.append({
                            "filename": uf.name,
                            "path": tmp_path,
                            "data": None,
                            "errore": str(e),
                        })

            st.session_state["import_previews"] = previews
            st.session_state["import_temp_paths"] = temp_paths
            st.rerun()

    # ── Preview results ──
    if "import_previews" in st.session_state and st.session_state["import_previews"]:
        previews = st.session_state["import_previews"]

        st.subheader("📋 Riepilogo importazione")

        valid = [p for p in previews if p.get("data") and not p.get("errore")]
        errors = [p for p in previews if p.get("errore")]
        new_persone = [p for p in valid if not p.get("persona_esistente")]

        col1, col2, col3 = st.columns(3)
        col1.metric("File validi", len(valid))
        col2.metric("Persone da creare", len(new_persone))
        col3.metric("Errori", len(errors), delta=None if not errors else f"-{len(errors)}", delta_color="inverse" if errors else "off")

        df_preview = pd.DataFrame([{
            "File": p["filename"],
            "Anno": p.get("anno", "—"),
            "CF": p.get("cf", "—"),
            "Persona": f"{p.get('cognome', '—')} {p.get('nome', '—')}",
            "Stato persona": "✅ Esistente" if p.get("persona_esistente") else "🆕 Da creare",
            "Reddito": p.get("reddito", "—"),
            "Imposta netta": p.get("imposta_netta", "—"),
            "Differenza": p.get("differenza", "—"),
            "Validazione": "✅" if p.get("validazione_ok") is True else ("❌" if p.get("validazione_ok") is False else "—"),
            "Errore": p.get("errore", ""),
        } for p in previews])
        st.dataframe(df_preview, use_container_width=True, hide_index=True)

        # Expanded detail per file
        for p in valid:
            with st.expander(f"📄 {p['filename']} — {p['anno']} — {p.get('cognome','')} {p.get('nome','')}"):
                pl = p["data"].get("prospetto_liquidazione", {})
                pl_rows = []
                for k, v in sorted(pl.items()):
                    if isinstance(v, dict):
                        pl_rows.append({
                            "Rigo/Col": k.replace("rigo_", "").replace("_col_", "/"),
                            "Descrizione": v.get("descrizione", ""),
                            "Valore": v.get("valore"),
                        })
                if pl_rows:
                    st.dataframe(pd.DataFrame(pl_rows), use_container_width=True, hide_index=True)

        # Bulk confirm
        col_btn, col_clr = st.columns([2, 1])
        with col_btn:
            if st.button("✅ Conferma e Salva tutti", type="primary", disabled=not valid):
                imported = 0
                created_persone = 0
                failed = []

                with st.spinner(f"Salvataggio {len(valid)} dichiarazioni..."):
                    for p in valid:
                        try:
                            dich, persona, persona_created = import_pdf_to_db(p["path"], session)
                            imported += 1
                            if persona_created:
                                created_persone += 1
                        except Exception as e:
                            failed.append((p["filename"], str(e)))
                            session.rollback()

                # Cleanup temp files
                for tp in st.session_state.get("import_temp_paths", []):
                    Path(tp).unlink(missing_ok=True)

                if imported:
                    msg = f"✅ {imported} dichiarazione{'i' if imported != 1 else ''} importata{'e' if imported != 1 else ''}"
                    if created_persone:
                        msg += f" — {created_persone} nuova{' persona' if created_persone == 1 else ' persone'} creata{'e' if created_persone != 1 else ''}"
                    st.success(msg)
                if failed:
                    for fname, err in failed:
                        st.error(f"Errore {fname}: {err}")

                del st.session_state["import_previews"]
                st.session_state.pop("import_temp_paths", None)
                st.rerun()

        with col_clr:
            if st.button("🗑️ Annulla"):
                for tp in st.session_state.get("import_temp_paths", []):
                    Path(tp).unlink(missing_ok=True)
                del st.session_state["import_previews"]
                st.session_state.pop("import_temp_paths", None)
                st.rerun()

# ── Riepilogo Annuale ───────────────────────────────────────────────

elif page == "📊 Riepilogo Annuale":
    st.title(f"Riepilogo {anno}")

    if not selected_persona:
        st.warning("Seleziona una persona nella sidebar")
    else:
        dich = session.query(Dichiarazione).filter_by(
            persona_id=selected_persona.id, anno_fiscale=anno
        ).first()

        if not dich or not dich.risultato:
            st.info(f"Nessun dato per {anno}. Importa un PDF nella sezione Importa.")
        else:
            r = dich.risultato
            aliquota = (r.imposta_netta / r.reddito_complessivo * 100) if r.reddito_complessivo else 0

            cols = st.columns(4)
            cols[0].metric("Reddito Complessivo", f"€ {r.reddito_complessivo:,.0f}")
            cols[1].metric("Imposta Netta", f"€ {r.imposta_netta:,.0f}")
            cols[2].metric("Aliquota Effettiva", f"{aliquota:.1f}%")
            cols[3].metric(
                "Esito",
                f"€ {abs(r.differenza):,.0f}",
                delta="credito" if r.esito == "credito" else "- debito",
                delta_color="normal" if r.esito == "credito" else "inverse",
            )

            # Quadro C
            st.subheader("Quadro C — Lavoro Dipendente")
            qc_entries = session.query(QuadroC_Lavoro).filter_by(dichiarazione_id=dich.id).all()
            if qc_entries:
                df_c = pd.DataFrame([{
                    "Reddito": f"€ {q.reddito:,.0f}" if q.reddito else "—",
                    "Ritenute": f"€ {q.ritenute:,.0f}" if q.ritenute else "—",
                    "Giorni": q.giorni or "—",
                } for q in qc_entries if q.reddito or q.ritenute])
                if not df_c.empty:
                    st.dataframe(df_c, use_container_width=True)

            # Quadro B — Immobili
            st.subheader("Quadro B — Immobili")
            qb_entries = session.query(QuadroB_Fabbricati).filter_by(dichiarazione_id=dich.id).all()
            if qb_entries:
                df_b = pd.DataFrame([{
                    "Rigo": q.rigo,
                    "Rendita catastale": f"€ {q.rendita:,.0f}" if q.rendita else "—",
                    "Utilizzo": UTILIZZO_MAP.get(int(q.utilizzo), q.utilizzo) if q.utilizzo and str(q.utilizzo).isdigit() else q.utilizzo or "—",
                    "Giorni": q.giorni_possesso or "—",
                    "% Possesso": f"{q.percentuale:.0f}%" if q.percentuale else "—",
                } for q in qb_entries])
                st.dataframe(df_b, use_container_width=True, hide_index=True)
            else:
                st.caption("Nessun immobile dichiarato")

            # Quadro E — Oneri con raggruppamento
            st.subheader("Quadro E — Oneri Detraibili")
            oneri = session.query(QuadroE_Oneri).filter_by(dichiarazione_id=dich.id).all()
            if oneri:
                # Group by category
                category_totals = {}
                for o in oneri:
                    code = o.codice_rigo
                    base_code = code.split(".")[0] if "." in code else code
                    cat = _oneri_category(base_code, o.descrizione)
                    category_totals[cat] = category_totals.get(cat, 0) + (o.importo or 0)

                df_e = pd.DataFrame([
                    {"Categoria": c, "Totale": f"€ {v:,.0f}"}
                    for c, v in sorted(category_totals.items(), key=lambda x: -x[1])
                ])
                st.dataframe(df_e, use_container_width=True, hide_index=True)

                # Impact
                totale = sum(o.importo or 0 for o in oneri)
                if r.imposta_netta and r.ritenute:
                    imposta_lorda_approx = abs(r.imposta_netta - r.differenza) if r.differenza else r.imposta_netta
                    if imposta_lorda_approx > 0:
                        impact = totale / imposta_lorda_approx * 100
                        st.caption(f"Totale oneri: € {totale:,.0f} — impatto ~{impact:.1f}% sull'imposta lorda")

                # Full detail expander
                with st.expander("Dettaglio completo"):
                    df_full = pd.DataFrame([{
                        "Codice": o.codice_rigo,
                        "Descrizione": o.descrizione,
                        "Importo": f"€ {o.importo:,.0f}" if o.importo else "—",
                    } for o in oneri])
                    st.dataframe(df_full, use_container_width=True, hide_index=True)
            else:
                st.caption("Nessun onere detraibile registrato")


# ── Trend ────────────────────────────────────────────────────────────

elif page == "📈 Trend":
    st.title("Trend Interannuali")

    if not selected_persona:
        st.warning("Seleziona una persona nella sidebar")
    else:
        records = (
            session.query(Dichiarazione, Risultato)
            .join(Risultato, Risultato.dichiarazione_id == Dichiarazione.id)
            .filter(Dichiarazione.persona_id == selected_persona.id)
            .order_by(Dichiarazione.anno_fiscale)
            .all()
        )

        if not records:
            st.info("Nessun dato disponibile. Importa qualche dichiarazione prima.")
        else:
            anni = [d.anno_fiscale for d, _ in records]
            redditi = [r.reddito_complessivo or 0 for _, r in records]
            imposte = [r.imposta_netta or 0 for _, r in records]
            ritenute_vals = [r.ritenute or 0 for _, r in records]
            differenze = [r.differenza or 0 for _, r in records]
            imposte_lorde = [r.imposta_lorda or 0 for _, r in records]

            df = pd.DataFrame({
                "Anno": anni,
                "Reddito Complessivo": redditi,
                "Imposta Netta": imposte,
                "Ritenute": ritenute_vals,
            })

            tab1, tab2, tab3, tab4 = st.tabs([
                "Reddito e Imposte", "Detrazioni e Oneri",
                "Differenza", "Proiezione",
            ])

            # ── Tab 1: Reddito e Imposte ──
            with tab1:
                fig = px.line(df, x="Anno", y=["Reddito Complessivo", "Imposta Netta", "Ritenute"],
                              markers=True, title="Trend Reddito, Imposta e Ritenute")
                aliquote = [
                    (r.imposta_netta / r.reddito_complessivo * 100)
                    if r.reddito_complessivo else 0
                    for _, r in records
                ]
                fig.add_scatter(x=anni, y=aliquote, mode="lines+markers",
                                name="Aliquota Effettiva (%)", yaxis="y2")
                fig.update_layout(
                    yaxis_title="Euro (€)",
                    yaxis2=dict(title="%", overlaying="y", side="right"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(fig, use_container_width=True)

                addiz_data = []
                for d, r in records:
                    addiz_data.append({
                        "Anno": d.anno_fiscale,
                        "Addiz. Regionale Certificazione": r.addiz_regionale_certificazione or 0,
                        "Addiz. Comunale Certificazione": r.addiz_comunale_certificazione or 0,
                    })
                if addiz_data and any(row["Addiz. Regionale Certificazione"] or row["Addiz. Comunale Certificazione"] for row in addiz_data):
                    st.subheader("Addizionali regionali e comunali")
                    df_add = pd.DataFrame(addiz_data)
                    fig_add = px.line(df_add, x="Anno", y=["Addiz. Regionale Certificazione", "Addiz. Comunale Certificazione"],
                                      markers=True)
                    fig_add.update_layout(yaxis_title="Euro (€)")
                    st.plotly_chart(fig_add, use_container_width=True)

            # ── Tab 2: Detrazioni e Oneri ──
            with tab2:
                st.subheader("Detrazioni Prospetto di Liquidazione")
                pl_detrazioni = []
                for d, r in records:
                    pl_detrazioni.append({
                        "Anno": d.anno_fiscale,
                        "Lavoro dipendente": r.detrazione_lavoro_dipendente or 0,
                        "Oneri": r.detrazione_oneri or 0,
                        "Recupero edilizio": r.detrazione_recupero_edilizio or 0,
                        "Risparmio energetico": r.detrazione_risparmio_energetico or 0,
                    })
                if pl_detrazioni:
                    df_pl = pd.DataFrame(pl_detrazioni)
                    fig_pl = px.line(df_pl, x="Anno",
                                     y=["Lavoro dipendente", "Oneri", "Recupero edilizio", "Risparmio energetico"],
                                     markers=True,
                                     title="Detrazioni PL per anno")
                    fig_pl.update_layout(yaxis_title="Euro (€)")
                    st.plotly_chart(fig_pl, use_container_width=True)

                st.subheader("Oneri per categoria (Quadro E)")
                oneri_per_anno = {}
                for d, _ in records:
                    oneri = session.query(QuadroE_Oneri).filter_by(dichiarazione_id=d.id).all()
                    cats = {}
                    for o in oneri:
                        base_code = o.codice_rigo.split(".")[0] if "." in o.codice_rigo else o.codice_rigo
                        cat = _oneri_category(base_code, o.descrizione)
                        broad = {
                            "Spese sanitarie": "Spese sanitarie",
                            "Spese sanitarie (disabilità)": "Spese sanitarie",
                            "Spese sanitarie (patologie esenti)": "Spese sanitarie",
                            "Interessi mutuo prima casa": "Interessi mutuo",
                            "Assicurazioni vita/infortuni": "Assicurazioni",
                            "Spese istruzione": "Istruzione",
                            "Spese universitarie": "Istruzione",
                            "Recupero edilizio": "Recupero edilizio",
                            "Risparmio energetico": "Risparmio energetico",
                        }.get(cat, "Altro")
                        cats[broad] = cats.get(broad, 0) + (o.importo or 0)
                    oneri_per_anno[d.anno_fiscale] = cats

                if oneri_per_anno:
                    all_cats = sorted({c for cats in oneri_per_anno.values() for c in cats})
                    oneri_df = pd.DataFrame([
                        {"Anno": anno, **{c: cats.get(c, 0) for c in all_cats}}
                        for anno, cats in oneri_per_anno.items()
                    ])
                    fig_oneri = px.bar(oneri_df, x="Anno", y=all_cats,
                                       title="Composizione oneri per macrocategoria",
                                       labels={"value": "Euro (€)", "variable": "Categoria"})
                    st.plotly_chart(fig_oneri, use_container_width=True)

            # ── Tab 3: Differenza ──
            with tab3:
                fig2 = go.Figure()
                colors = ["green" if d < 0 else "red" for d in differenze]
                fig2.add_trace(go.Bar(x=anni, y=differenze, marker_color=colors,
                                      text=[f"€ {d:,.0f}" for d in differenze],
                                      textposition="outside"))
                fig2.update_layout(title="Differenza anno per anno (negativo = credito)",
                                   yaxis_title="Euro (€)")
                st.plotly_chart(fig2, use_container_width=True)

                st.subheader("Variazioni anno su anno")
                delta_data = []
                for i in range(1, len(anni)):
                    prev_r = redditi[i-1]
                    curr_r = redditi[i]
                    pct = ((curr_r - prev_r) / prev_r * 100) if prev_r else 0
                    delta_data.append({
                        "Transizione": f"{anni[i-1]} → {anni[i]}",
                        "Δ Reddito": f"€ {curr_r - prev_r:+,.0f} ({pct:+.1f}%)",
                        "Δ Imposta": f"€ {imposte[i] - imposte[i-1]:+,.0f}",
                    })
                if delta_data:
                    st.dataframe(pd.DataFrame(delta_data), use_container_width=True, hide_index=True)

            # ── Tab 4: Proiezione ──
            with tab4:
                st.subheader("Rate residue lavori edilizi")
                last_dich, last_r = records[-1]
                ultimo_anno = last_dich.anno_fiscale

                rate_codes = {"E41", "E42", "E43", "E61"}
                rate_rigos = {41: "E41", 42: "E42", 43: "E43", 61: "E61"}
                rate_rows = []

                for rigo, code in rate_rigos.items():
                    oneri_code = session.query(QuadroE_Oneri).filter_by(
                        dichiarazione_id=last_dich.id, codice_rigo=code
                    ).all()
                    if not oneri_code:
                        oneri_code = session.query(QuadroE_Oneri).filter_by(
                            dichiarazione_id=last_dich.id, codice_rigo=f"{code}.col8"
                        ).all()
                    if not oneri_code:
                        oneri_code = session.query(QuadroE_Oneri).filter_by(
                            dichiarazione_id=last_dich.id, codice_rigo=f"{code}.col9"
                        ).all()

                    if oneri_code:
                        importo_spesa = max(o.importo or 0 for o in oneri_code)
                        if importo_spesa:
                            first_year = session.query(Dichiarazione.anno_fiscale)\
                                .join(QuadroE_Oneri, QuadroE_Oneri.dichiarazione_id == Dichiarazione.id)\
                                .filter(
                                    Dichiarazione.persona_id == selected_persona.id,
                                    QuadroE_Oneri.codice_rigo.in_([code, f"{code}.col8", f"{code}.col9"]),
                                ).order_by(Dichiarazione.anno_fiscale).first()
                            anno_spesa = first_year[0] if first_year else ultimo_anno
                            rata_corrente = min(ultimo_anno - anno_spesa + 1, 10)
                            detrazione_annua = round(importo_spesa / 10, 2)
                            anni_residui = max(0, 10 - rata_corrente)
                            importo_residuo = round(detrazione_annua * anni_residui, 2)
                            rate_rows.append({
                                "Rigo": code,
                                "Anno spesa": anno_spesa,
                                "Rata": f"{rata_corrente}/10",
                                "Spesa totale €": f"{importo_spesa:,.0f}",
                                "Detrazione annua €": f"{detrazione_annua:,.0f}",
                                "Anni residui": anni_residui,
                                "Residuo €": f"{importo_residuo:,.0f}",
                            })

                if rate_rows:
                    st.dataframe(pd.DataFrame(rate_rows), use_container_width=True, hide_index=True)

                    st.subheader("Credito stimato — prossimi 10 anni")
                    tot_detrazioni_edilizie_annue = sum(
                        float(r["Detrazione annua €"].replace(",", "").replace("€", "").strip())
                        for r in rate_rows
                    )
                    detrazione_lavoro_base = last_r.detrazione_lavoro_dipendente or 0
                    detrazione_oneri_base = last_r.detrazione_oneri or 0
                    detrazione_recupero_base = last_r.detrazione_recupero_edilizio or 0
                    detrazione_energetica_base = last_r.detrazione_risparmio_energetico or 0
                    imposta_lorda_base = last_r.imposta_lorda or 0
                    ritenute_base = last_r.ritenute or 0
                    reddito_base = last_r.reddito_complessivo or 0

                    proiezione_anni = list(range(ultimo_anno + 1, ultimo_anno + 11))
                    crediti_con = []
                    crediti_senza = []

                    for i, af in enumerate(proiezione_anni):
                        anni_passati = i + 1
                        detrazioni_attive = sum(
                            detrazione_annua
                            for r in rate_rows
                            if (detrazione_annua := float(r["Detrazione annua €"].replace(",", "").replace("€", "").strip()))
                            and r["Anni residui"] >= anni_passati
                        )
                        tot_detrazioni_stimato = (
                            detrazione_lavoro_base
                            + detrazione_oneri_base
                            + detrazione_recupero_base
                            + detrazione_energetica_base
                        )
                        imposta_stimata = max(0, imposta_lorda_base - tot_detrazioni_stimato - detrazioni_attive)
                        credito_con = ritenute_base - imposta_stimata
                        crediti_con.append(credito_con)

                        imposta_stimata_senza = max(0, imposta_lorda_base - tot_detrazioni_stimato)
                        credito_senza = ritenute_base - imposta_stimata_senza
                        crediti_senza.append(credito_senza)

                    fig_proj = go.Figure()
                    fig_proj.add_trace(go.Bar(x=proiezione_anni, y=crediti_con,
                                              name="Con detrazioni edilizie",
                                              marker_color="green"))
                    fig_proj.add_trace(go.Bar(x=proiezione_anni, y=crediti_senza,
                                              name="Senza detrazioni edilizie",
                                              marker_color="orange"))
                    fig_proj.update_layout(
                        title="Stima credito / debito futuri",
                        yaxis_title="Euro (€)",
                        barmode="group",
                    )
                    st.plotly_chart(fig_proj, use_container_width=True)

                    st.caption(
                        f"⚠️ **Stima indicativa.** Basata sui dati {ultimo_anno}: "
                        f"reddito €{reddito_base:,.0f}, ritenute €{ritenute_base:,.0f}. "
                        "Si assume reddito e ritenute costanti per gli anni futuri. "
                        "La situazione reale può variare."
                    )
                else:
                    st.info("Nessuna detrazione edilizia multi-annuale trovata per l'ultimo anno.")


# ── Alert ────────────────────────────────────────────────────────────

elif page == "🔔 Alert":
    st.title("Alert e Anomalie")

    if not selected_persona:
        st.warning("Seleziona una persona nella sidebar")
    else:
        sensitivity = st.sidebar.slider("Soglia alert (%)", 10, 50, 20, 5)

        alerts = []

        # Get all years
        records = (
            session.query(Dichiarazione, Risultato)
            .join(Risultato)
            .filter(Dichiarazione.persona_id == selected_persona.id)
            .order_by(Dichiarazione.anno_fiscale)
            .all()
        )

        if len(records) < 2:
            st.info("Servono almeno 2 anni di dati per generare alert.")
        else:
            for i in range(1, len(records)):
                prev_dich, prev_r = records[i-1]
                curr_dich, curr_r = records[i]

                # Income anomaly
                if prev_r.reddito_complessivo and curr_r.reddito_complessivo and prev_r.reddito_complessivo > 0:
                    income_pct = abs((curr_r.reddito_complessivo - prev_r.reddito_complessivo) / prev_r.reddito_complessivo * 100)
                    if income_pct > sensitivity:
                        direction = "aumento" if curr_r.reddito_complessivo > prev_r.reddito_complessivo else "calo"
                        alerts.append({
                            "tipo": "📈 Reddito",
                            "messaggio": f"Reddito: {direction} del {income_pct:.1f}% da {prev_dich.anno_fiscale} ({prev_r.reddito_complessivo:,.0f}€) a {curr_dich.anno_fiscale} ({curr_r.reddito_complessivo:,.0f}€)",
                            "severity": "warning" if income_pct > 30 else "info",
                        })

                # Missing deductions check
                prev_oneri = session.query(QuadroE_Oneri).filter_by(dichiarazione_id=prev_dich.id).all()
                curr_oneri = session.query(QuadroE_Oneri).filter_by(dichiarazione_id=curr_dich.id).all()
                prev_codes = {o.codice_rigo for o in prev_oneri}
                curr_codes = {o.codice_rigo for o in curr_oneri}

                for code in prev_codes - curr_codes:
                    desc = next((o.descrizione for o in prev_oneri if o.codice_rigo == code), code)
                    alerts.append({
                        "tipo": "⚠️ Detrazione mancante",
                        "messaggio": f"{desc} ({code}): presente nel {prev_dich.anno_fiscale}, assente nel {curr_dich.anno_fiscale}",
                        "severity": "warning",
                    })

                # Significant drop in deductions
                for p_onere in prev_oneri:
                    for c_onere in curr_oneri:
                        if p_onere.codice_rigo == c_onere.codice_rigo and p_onere.importo and c_onere.importo:
                            if p_onere.importo > 0:
                                drop_pct = (p_onere.importo - c_onere.importo) / p_onere.importo * 100
                                if drop_pct > sensitivity:
                                    alerts.append({
                                        "tipo": "📉 Calo detrazione",
                                        "messaggio": f"{p_onere.descrizione} ({p_onere.codice_rigo}): calo del {drop_pct:.1f}% da {p_onere.importo:,.0f}€ a {c_onere.importo:,.0f}€",
                                        "severity": "error" if drop_pct > 50 else "warning",
                                    })

            if alerts:
                st.subheader(f"🔔 {len(alerts)} alert trovati")
                for a in alerts:
                    if a["severity"] == "error":
                        st.error(f"**{a['tipo']}**: {a['messaggio']}")
                    elif a["severity"] == "warning":
                        st.warning(f"**{a['tipo']}**: {a['messaggio']}")
                    else:
                        st.info(f"**{a['tipo']}**: {a['messaggio']}")
            else:
                st.success("✅ Nessuna anomalia rilevata")


session.close()

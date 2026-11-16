# La Fábrica de Baltasares

Plataforma solidaria que recoge juguetes donados y los hace llegar a niños de familias en situación de necesidad y a
organizaciones, con emparejamiento a partir de la carta a los Reyes, seguimiento de cada juguete y un dashboard de
impacto para las empresas que financian la logística.

Proyecto universitario · Grado en Business Data Analytics · *Modelos de negocio en el ámbito de los datos* ·
Mondragon Unibertsitatea. **Todos los datos son ficticios (datos de demostración).**

## Ejecución

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Secretos

En Streamlit Community Cloud: *App settings → Secrets* (en local, `.streamlit/secrets.toml`, que no se sube):

```toml
panel_password = "contraseña-del-panel"
# ANTHROPIC_API_KEY = "..."   # opcional: interpretación de cartas con IA; sin ella se usan reglas
```

Los datos se guardan en una base SQLite local: cuando la app se reinicia o se duerme por inactividad, vuelve a los
datos de demostración.

## Códigos de demostración

| Para qué | Valor |
|---|---|
| Código de entidad (familias) | `REYES-DEUSTO`, `REYES-CARITAS`, `REYES-REKALDE` |
| Código de organización | `ORG-LAGUNAK`, `ORG-ETXEBERRI`, `ORG-ITSASALDEA`, `ORG-GOIKOA` |
| Código de campaña (dashboard de empresa) | `LANTEGI-2026`, `TXOKOA-2026` |

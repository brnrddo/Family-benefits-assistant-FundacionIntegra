# 🤝 Cómo colaborar sin romper nada

Guía rápida para subir tus aportes trabajando desde **Kiro**. Pensada para que no haga falta ser experto en git.

---

## 🧭 El ciclo de trabajo (memorízalo)

```
   PULL  →  trabajar  →  COMMIT  →  PUSH
 (bajar)              (guardar)   (subir)
```

Todo esto se hace desde el panel **Source Control** de Kiro (ícono de ramas en la barra izquierda, o `Ctrl+Shift+G`).

---

## 1️⃣ Antes de empezar: PULL (bajar lo nuevo)

Siempre trae primero los cambios de los demás para no trabajar sobre algo viejo:

- Abre **Source Control** → menú `...` (arriba) → **Pull**.

---

## 2️⃣ Mientras trabajas: COMMIT (guardar tu avance)

1. Haz tus cambios (edita archivos, crea cosas, etc.).
2. En **Source Control** verás la lista de archivos modificados.
3. Pulsa el `+` junto a cada archivo (o el `+` general) para prepararlos ("stage").
4. Escribe un mensaje corto que explique qué hiciste, por ejemplo:
   - `Agrego pantalla de login`
   - `Conecto la base de datos`
   - `Mejoro el prompt de la IA`
5. Pulsa **Commit**.

> 💡 Haz commits pequeños y seguido. Es más fácil de ordenar que un commit gigante al final.

---

## 3️⃣ Al terminar: PUSH (subir a GitHub)

- **Source Control** → menú `...` → **Push**.
- La primera vez te pedirá autorizar GitHub en el navegador. Después ya no.

---

## 🧩 Para no pisarnos entre nosotros

Trabajamos en estas carpetas; idealmente cada quien en la suya:

- `frontend/` — interfaz
- `backend/` — API / servidor
- `database/` — base de datos
- `ia/` — IA generativa

Si dos personas tocan el **mismo archivo** a la vez puede salir un **conflicto**. No pasa nada, se arregla:

### ⚠️ Si aparece un "conflicto" (merge conflict)
1. Kiro te marca el archivo en conflicto y resalta las dos versiones.
2. Verás algo así en el archivo:
   ```
   <<<<<<< tu versión
   ...
   =======
   ...
   >>>>>>> versión de otra persona
   ```
3. Kiro muestra botones **"Accept Current"**, **"Accept Incoming"** o **"Accept Both"**. Elige lo correcto (si dudas, **pregunta al equipo antes de aceptar**).
4. Guarda, haz **Commit** y luego **Push**.

> 🆘 Si te trabas, no fuerces nada: avisa en el chat del equipo. Es mejor preguntar que romper el repo.

---

## ✅ Buenas prácticas rápidas

- 🔄 **Pull antes de empezar, Push al terminar.** Siempre.
- 🔐 Nunca subas el `.env` ni claves (ver reglas de seguridad en el [README](./README.md)).
- 📝 Mensajes de commit claros y cortos.
- 🧪 Antes de hacer Push, revisa que lo tuyo al menos abre/funciona.
- 🙋 Ante la duda, pregunta en el chat del equipo. Nadie se enoja por preguntar.

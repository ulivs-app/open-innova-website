# Contact Form

Drop-in HTML form that builds a `mailto:` URL with prefilled subject and body, then opens the user's mail client. Zero backend, zero third-party services, zero cookies.

The form handler lives in [`assets/js/scripts.js`](../assets/js/scripts.js) and is auto-attached to any `<form class="contact-form">` on the page. Styling is in [`assets/css/style.css`](../assets/css/style.css) under the `Contact form` section.

---

## Copy-paste example

Paste this HTML into any Markdown page (`unsafe = true` is already set in `hugo.toml`, so raw HTML is allowed).

```html
<form class="contact-form" data-fallback-recipient="info@openinnova.it">
  <div class="form-grid">
    <div class="form-row">
      <label for="contact-name">Nome <span class="form-required">*</span></label>
      <input type="text" id="contact-name" name="name" placeholder="Mario Rossi" required autocomplete="name">
    </div>
    <div class="form-row">
      <label for="contact-email">Email <span class="form-required">*</span></label>
      <input type="email" id="contact-email" name="email" placeholder="mario.rossi@esempio.it" required autocomplete="email">
    </div>
    <div class="form-row">
      <label for="contact-phone">Telefono <span class="form-optional">(opzionale)</span></label>
      <input type="tel" id="contact-phone" name="phone" placeholder="+39 333 1234567" autocomplete="tel">
    </div>
    <div class="form-row">
      <label for="contact-topic">Tipo di richiesta</label>
      <select id="contact-topic" name="topic">
        <option value="info" data-recipient="info@openinnova.it" selected>Informazioni generali</option>
        <option value="consulenza" data-recipient="info@openinnova.it">Consulenza</option>
        <option value="prodotti" data-recipient="info@openinnova.it">Prodotti / demo</option>
        <option value="dev" data-recipient="dev@openinnova.it">Software su misura</option>
        <option value="altro" data-recipient="info@openinnova.it">Altro</option>
      </select>
    </div>
  </div>
  <div class="form-row">
    <label for="contact-message">Messaggio</label>
    <textarea id="contact-message" name="message" rows="5" placeholder="Raccontaci di cosa hai bisogno e come possiamo esserti utili…"></textarea>
  </div>
  <div class="form-actions">
    <button type="submit" class="btn btn-primary">Invia</button>
    <button type="reset" class="btn btn-outline">Cancella</button>
  </div>
</form>
```

---

## Required structure

The JS handler depends on these conventions — keep them as-is:

| Element | Requirement |
|---|---|
| `<form>` | class `contact-form`; `data-fallback-recipient="email@example.com"` provides the recipient used when no `<option>` is selected (no `action` attribute — keeps Chrome from flagging the page as "not fully secure" for non-HTTPS form submission) |
| `<input id="contact-name">` | required field, picked up by name |
| `<input id="contact-email">` | required field, picked up by email |
| `<input id="contact-phone">` | optional, included in the body only if filled |
| `<textarea id="contact-message">` | message body |
| `<select id="contact-topic">` | each `<option>` MUST carry a `data-recipient="…"` — overrides the form's `action` |

The handler also reads `document.documentElement.lang` and switches the email greeting/sign-off between Italian and English. No extra config needed for the EN page — just translate the labels and option text in the HTML.

---

## Generated email

With the example above, submitting the form opens the user's mail client pre-filled like:

```
To:      info@openinnova.it
Subject: [Consulenza] Richiesta da Mario Rossi — openinnova.it

Buongiorno,

vi scrivo tramite il modulo di contatto di openinnova.it in merito a "Consulenza".

I miei recapiti:
· Nome: Mario Rossi
· Email: mario.rossi@esempio.it
· Telefono: +39 333 1234567

[user message here]

Cordiali saluti,
Mario Rossi
```

---

## Live instances

- IT: [`content/it/contatti.md`](../content/it/contatti.md)
- EN: [`content/en/contact.md`](../content/en/contact.md)

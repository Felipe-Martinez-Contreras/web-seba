// Estado "cargando" en los formularios que se envían sin HTMX: marca el botón de envío
// como ocupado y evita el doble envío. Los formularios con HTMX usan la clase htmx-request.
document.addEventListener("submit", function (evento) {
  var formulario = evento.target;
  if (!(formulario instanceof HTMLFormElement) || formulario.hasAttribute("hx-post")) {
    return;
  }
  if (formulario.dataset.enviando === "si") {
    evento.preventDefault();
    return;
  }
  formulario.dataset.enviando = "si";
  formulario.querySelectorAll("button[type=submit], button:not([type])").forEach(function (boton) {
    boton.setAttribute("aria-busy", "true");
    boton.setAttribute("aria-disabled", "true");
  });
});

// Al volver con el botón "atrás" del navegador, el formulario debe poder enviarse de nuevo.
window.addEventListener("pageshow", function () {
  document.querySelectorAll("form[data-enviando]").forEach(function (formulario) {
    delete formulario.dataset.enviando;
    formulario.querySelectorAll("button[aria-busy]").forEach(function (boton) {
      boton.removeAttribute("aria-busy");
      boton.removeAttribute("aria-disabled");
    });
  });
});

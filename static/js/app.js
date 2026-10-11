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

document.addEventListener("click", function (evento) {
  if (!(evento.target instanceof Element)) {
    return;
  }

  // Mostrar u ocultar la contraseña.
  var alternador = evento.target.closest("[data-alterna-contrasena]");
  if (alternador) {
    var entrada = document.getElementById(alternador.dataset.alternaContrasena);
    if (entrada) {
      var mostrar = entrada.type === "password";
      entrada.type = mostrar ? "text" : "password";
      alternador.setAttribute("aria-pressed", mostrar ? "true" : "false");
      alternador.setAttribute("aria-label", mostrar ? "Ocultar contraseña" : "Mostrar contraseña");
    }
    return;
  }

  // Abrir un diálogo de confirmación. Se cierra solo: "Cancelar" usa method="dialog".
  var disparador = evento.target.closest("[data-abre-dialogo]");
  if (disparador) {
    var dialogo = document.getElementById(disparador.dataset.abreDialogo);
    if (dialogo instanceof HTMLDialogElement) {
      dialogo.showModal();
    }
  }

  // Copiar al portapapeles el texto de un campo de solo lectura.
  var copiador = evento.target.closest("[data-copia]");
  if (copiador) {
    var origen = document.getElementById(copiador.dataset.copia);
    if (origen instanceof HTMLInputElement) {
      copiar(origen);
    }
  }
});

// Tras un envío con errores, el foco va al resumen: quien usa teclado o lector de pantalla
// queda arriba del formulario y escucha qué pasó.
document.addEventListener("DOMContentLoaded", function () {
  var resumen = document.querySelector("[data-enfocar]");
  if (resumen) {
    resumen.focus();
  }
});

// Escape cierra el menú desplegable abierto y devuelve el foco al botón que lo abrió.
document.addEventListener("keydown", function (evento) {
  if (evento.key !== "Escape") {
    return;
  }
  document.querySelectorAll("details[open] > .menu-flotante").forEach(function (menu) {
    var desplegable = menu.parentElement;
    desplegable.removeAttribute("open");
    var boton = desplegable.querySelector("summary");
    if (boton) {
      boton.focus();
    }
  });
});

// Un menú desplegable abierto se cierra al hacer clic fuera de él.
document.addEventListener("click", function (evento) {
  document.querySelectorAll("details[open] > .menu-flotante").forEach(function (menu) {
    var desplegable = menu.parentElement;
    if (!(evento.target instanceof Node) || !desplegable.contains(evento.target)) {
      desplegable.removeAttribute("open");
    }
  });
});

function copiar(origen) {
  var estado = document.getElementById(origen.id + "-estado");
  function avisar(texto) {
    if (estado) {
      estado.textContent = texto;
    }
  }
  origen.select();
  // El portapapeles solo existe en contextos seguros (HTTPS o localhost).
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(origen.value).then(
      function () {
        avisar("Copiado al portapapeles.");
      },
      function () {
        avisar("No se pudo copiar. El texto quedó seleccionado: cópielo con Ctrl+C.");
      }
    );
  } else {
    avisar("El texto quedó seleccionado: cópielo con Ctrl+C.");
  }
}

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

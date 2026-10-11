// Subida de documentos con progreso (ADM-08). Envía un archivo por petición, uno tras otro,
// con XMLHttpRequest (único camino con eventos de progreso de subida confiables), y muestra
// por cada archivo una barra <progress> y luego el resultado que responde el servidor.
// Sin este script el formulario se envía completo y la página muestra los mismos resultados.
// La validación de aquí es solo una ayuda: la que decide es la del servidor.
document.addEventListener("submit", function (evento) {
  var formulario = evento.target;
  if (!(formulario instanceof HTMLFormElement) || !formulario.dataset.subida) {
    return;
  }
  var entrada = formulario.querySelector('input[type="file"]');
  var lista = document.getElementById(formulario.dataset.subida);
  var token = formulario.querySelector('input[name="csrfmiddlewaretoken"]');
  if (!entrada || !lista || !token || !entrada.files || !entrada.files.length) {
    return;
  }
  evento.preventDefault();
  if (formulario.dataset.subiendo === "si") {
    return;
  }
  formulario.dataset.subiendo = "si";

  var maximo = Number(formulario.dataset.maximo) || 0;
  var archivos = Array.prototype.slice.call(entrada.files);
  lista.hidden = false;
  lista.textContent = "";
  var filas = archivos.map(function (archivo) {
    return crearFila(lista, archivo.name);
  });

  function terminar() {
    entrada.value = "";
    delete formulario.dataset.subiendo;
    delete formulario.dataset.enviando;
    formulario.querySelectorAll("button[aria-busy]").forEach(function (boton) {
      boton.removeAttribute("aria-busy");
      boton.removeAttribute("aria-disabled");
    });
    var cierre = document.createElement("li");
    cierre.className = "fila text-sm";
    var enlace = document.createElement("a");
    enlace.className = "enlace";
    enlace.href = formulario.dataset.lista || window.location.href;
    enlace.textContent = "Ver la lista de documentos actualizada";
    cierre.appendChild(enlace);
    lista.appendChild(cierre);
  }

  function subir(indice) {
    if (indice >= archivos.length) {
      terminar();
      return;
    }
    var archivo = archivos[indice];
    var fila = filas[indice];
    function siguiente() {
      subir(indice + 1);
    }
    if (maximo && archivo.size > maximo) {
      fallar(fila, "Supera el tamaño máximo de " + formulario.dataset.maximoMb + " MB. No se envió.");
      siguiente();
      return;
    }
    var datos = new FormData();
    datos.append("archivos", archivo);
    var peticion = new XMLHttpRequest();
    peticion.open("POST", formulario.action);
    peticion.setRequestHeader("X-CSRFToken", token.value);
    peticion.setRequestHeader("X-Subida", "fragmento");
    peticion.upload.addEventListener("progress", function (progreso) {
      if (progreso.lengthComputable) {
        avanzar(fila, Math.round((progreso.loaded / progreso.total) * 100));
      }
    });
    peticion.addEventListener("load", function () {
      if (peticion.status === 200 && peticion.responseText.trim()) {
        // El fragmento lo genera el servidor, con el nombre del archivo ya escapado.
        var plantilla = document.createElement("template");
        plantilla.innerHTML = peticion.responseText;
        fila.elemento.replaceWith(plantilla.content);
      } else {
        fallar(fila, "El servidor no aceptó la subida (error " + peticion.status + "). Recargue la página e intente de nuevo.");
      }
      siguiente();
    });
    peticion.addEventListener("error", function () {
      fallar(fila, "No se pudo conectar con el servidor. Revise su conexión e intente de nuevo.");
      siguiente();
    });
    peticion.send(datos);
  }

  subir(0);
});

function crearFila(lista, nombre) {
  var elemento = document.createElement("li");
  elemento.className = "fila flex-wrap";
  var textos = document.createElement("span");
  textos.className = "min-w-0 flex-1";
  var titulo = document.createElement("span");
  titulo.className = "fila-titulo block break-all";
  titulo.textContent = nombre;
  var estado = document.createElement("span");
  estado.className = "block text-sm";
  estado.textContent = "En espera";
  textos.appendChild(titulo);
  textos.appendChild(estado);
  var barra = document.createElement("progress");
  barra.className = "progreso";
  barra.max = 100;
  barra.value = 0;
  barra.setAttribute("aria-label", "Progreso de " + nombre);
  elemento.appendChild(textos);
  elemento.appendChild(barra);
  lista.appendChild(elemento);
  return { elemento: elemento, estado: estado, barra: barra };
}

function avanzar(fila, porcentaje) {
  fila.barra.value = porcentaje;
  fila.estado.textContent = porcentaje < 100 ? "Subiendo: " + porcentaje + " %" : "Comprobando el archivo";
}

function fallar(fila, motivo) {
  fila.barra.remove();
  fila.estado.textContent = "";
  var etiqueta = document.createElement("strong");
  etiqueta.className = "font-semibold text-error";
  etiqueta.textContent = "No se subió. ";
  fila.estado.appendChild(etiqueta);
  fila.estado.appendChild(document.createTextNode(motivo));
}

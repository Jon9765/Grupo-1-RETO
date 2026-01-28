document.addEventListener("DOMContentLoaded", function() {

    // ----------------------------
    // Inicializar mapa Leaflet
    // ----------------------------
    const map = L.map('map').setView([43.320324, -1.972454], 16);

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);

    const marker = L.marker([43.320324, -1.972454])
        .addTo(map)
        .bindPopup('<b>Trambot </b><br> Nuestra empresa <img src="img/empresa.webp" width="150px" height="100px">');

    marker.on('click', function() {
        marker.openPopup();
    });

    // ----------------------------
    // Botones de Stripe + panel_id
    // ----------------------------
    const botones = document.querySelectorAll(".plan-btn");

    console.log("Botones encontrados:", botones); // depuración

    botones.forEach(btn => {
        btn.addEventListener("click", function() {
            const priceId = btn.dataset.priceId;
            const panelId = btn.dataset.panelId;

            console.log("Redirigiendo a:", `/crear-suscripcion/${priceId}?panel_id=${panelId}`);
            window.location.href = `/crear-suscripcion/${priceId}?panel_id=${panelId}`;
        });
    });

});

function mostrarPanel(Num) {
    
    document.getElementById('main-panel').style.display = 'flex';
      switch (Num) {
        case 1:
          document.getElementById('panel1').style.display = 'block'
          break
        case 2:
          document.getElementById('panel2').style.display = 'block'

          break;
        case 3:
          document.getElementById('panel3').style.display = 'block'
          break;
          case 4:
          document.getElementById('panel4').style.display = 'block'
          break;
          case 5:
          document.getElementById('panel5').style.display = 'block'
          break;
      }
    
    }
    function cerrarPanel(Num) {
    document.getElementById('main-panel').style.display = 'none';
   switch (Num) {
        case 1:
          document.getElementById('panel1').style.display = 'none'
          break
        case 2:
          document.getElementById('panel2').style.display = 'none'
          break;
        case 3:
          document.getElementById('panel3').style.display = 'none'
          break;
        case 4:
          document.getElementById('panel4').style.display = 'none'
          break;
        case 5:
          document.getElementById('panel5').style.display = 'none'
          break;
      
        }
    }
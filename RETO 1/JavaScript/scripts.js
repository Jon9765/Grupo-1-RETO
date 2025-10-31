const map = L.map('map').setView([43.320324, -1.972454], 16);

const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
		maxZoom: 19,
		attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
	}).addTo(map);

const marker = L.marker([43.320324, -1.972454]).addTo(map)
    .bindPopup('<b>Trambot </b><br> Nuestra empresa <img src=img/empresa.webp width=150px height=100px>').onClick(openPopup());
    function mostrarPanel(valor) {
        switch(valor){
            case 1:
                document.getElementById('panel1').style.display = 'flex';
            case 2:
                document.getElementById('panel2').style.display = 'flex';
            case 3:
                document.getElementById('panel3').style.display = 'flex';
            case 4:
                document.getElementById('panel4').style.display = 'flex';
            case 5:
                document.getElementById('panel5').style.display = 'flex';
        }
      
    }
    function cerrarPanel(valor) {
       switch(valor){
            case 1:
                      document.getElementById('overlay').style.display = 'none';
            case 2:
                      document.getElementById('overlay').style.display = 'none';
            case 3:
                      document.getElementById('overlay').style.display = 'none';
            case 4:
                      document.getElementById('overlay').style.display = 'none';
            case 5:
                document.getElementById('overlay').style.display = 'none';
        }
    }


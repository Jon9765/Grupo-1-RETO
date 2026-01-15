const contenedor = document.getElementById("contenedor");
const registrarBtn = document.getElementById("registrar");
const loginBtn = document.getElementById("login");
const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const loginError = document.getElementById("loginError");
const registerError = document.getElementById("registerError");

registrarBtn.addEventListener('click', () => {
  contenedor.classList.add("active");
});

loginBtn.addEventListener('click', () => {
  contenedor.classList.remove("active");
});
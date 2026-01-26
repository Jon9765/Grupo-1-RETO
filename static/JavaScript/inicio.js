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



import axios from "axios";

const login = async (email, password) => {
  try {
    const response = await axios.post("http://localhost:5000/login", {
      email,
      password
    });
    
    // Guardar el token
    const token = response.data.token;
    localStorage.setItem("token", token);
    
  } catch (error) {
    console.error(error);
  }
};

const getUserData = async () => {
  const token = localStorage.getItem("token");
  const response = await axios.get("http://localhost:5000/api/servicios", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  return response.data;
};

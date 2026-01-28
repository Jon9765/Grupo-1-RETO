import axios from "axios";

const login = async (email, password) => {
  try {
    const response = await fetch("http://localhost:5000/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();

    if (data.success) {
      // Guardar el token en localStorage
      localStorage.setItem("token", data.token);
      localStorage.setItem("user_id", data.user_id);
      localStorage.setItem("nombre", data.nombre);

      console.log("✓ Token guardado:", data.token);
      return data;
    } else {
      console.error("✗ Error:", data.error);
    }
  } catch (error) {
    console.error(error);
  }
};

const getUserData = async () => {
  const token = localStorage.getItem("token");
  const response = await axios.get("http://localhost:5000/api/servicios", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.data;
};
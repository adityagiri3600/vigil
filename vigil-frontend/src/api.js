import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:5000/api", // change for deployment
});

export function setAuthToken(token) {
  if (token) {
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    localStorage.setItem("token", token);
  } else {
    delete api.defaults.headers.common["Authorization"];
    localStorage.removeItem("token");
  }
}

const token = localStorage.getItem("token");
if (token) {
  setAuthToken(token);
}

export default api;

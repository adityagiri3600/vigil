import React, { useState, useEffect } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import LoginPage from "./features/auth/LoginPage";
import SignupPage from "./features/auth/SignupPage";
import DashboardPage from "./features/dashboard/DashboardPage";
import FamilyPage from "./features/family/FamilyPage";
import NavBar from "./components/NavBar";

function ProtectedRoute({ children }) {
  const token = localStorage.getItem("token");
  const location = useLocation();
  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return children;
}

function App() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    // For this simple demo, we just rely on localStorage token
    // You can store user info there too if you want.
  }, []);

  return (
    <>
      <NavBar user={user} setUser={setUser} />
      <Routes>
        <Route path="/login" element={<LoginPage setUser={setUser} />} />
        <Route path="/signup" element={<SignupPage setUser={setUser} />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/family"
          element={
            <ProtectedRoute>
              <FamilyPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </>
  );
}

export default App;

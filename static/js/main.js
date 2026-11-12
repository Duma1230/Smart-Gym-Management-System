/**
 * Smart Gym Management System - Client Side Script
 */

document.addEventListener("DOMContentLoaded", () => {
    // Auto-dismiss flash alerts after 5 seconds
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach((alert) => {
        const closeBtn = alert.querySelector(".alert-close");
        if (closeBtn) {
            closeBtn.addEventListener("click", () => {
                alert.style.opacity = "0";
                setTimeout(() => alert.remove(), 200);
            });
        }

        setTimeout(() => {
            alert.style.transition = "opacity 0.4s ease";
            alert.style.opacity = "0";
            setTimeout(() => alert.remove(), 400);
        }, 5000);
    });

    // Password Match Validation helper for registration
    const registerForm = document.querySelector("#register-form");
    if (registerForm) {
        const password = document.querySelector("#password");
        const confirmPassword = document.querySelector("#confirm_password");

        registerForm.addEventListener("submit", (e) => {
            if (password && confirmPassword && password.value !== confirmPassword.value) {
                e.preventDefault();
                alert("Passwords do not match. Please verify.");
                confirmPassword.focus();
            }
        });
    }
});

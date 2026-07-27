const sidebar = document.querySelector("#bo-sidebar");
const overlay = document.querySelector(".bo-overlay");
document.querySelectorAll("[data-sidebar-open]").forEach((button) => {
    button.addEventListener("click", () => {
        sidebar?.classList.add("is-open");
        overlay?.classList.add("is-visible");
    });
});
document.querySelectorAll("[data-sidebar-close]").forEach((button) => {
    button.addEventListener("click", () => {
        sidebar?.classList.remove("is-open");
        overlay?.classList.remove("is-visible");
    });
});

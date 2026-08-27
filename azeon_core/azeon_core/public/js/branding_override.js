
document.addEventListener("DOMContentLoaded", function() {
    document.querySelectorAll("a, span, div").forEach(function(el) {
        if (el.textContent.trim() === "Home" && el.closest("header, nav, .navbar")) {
            el.textContent = "Azeon Systems";
        }
    });
});
                
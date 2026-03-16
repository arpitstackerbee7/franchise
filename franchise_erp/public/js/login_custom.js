console.log("LOGIN PAGE JS LOADED");

document.addEventListener("click", function (e) {

    const btn = e.target.closest("#login-again-btn");

    if (btn) {
        alert("Hello World");
    }

});
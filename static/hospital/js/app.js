document.addEventListener('DOMContentLoaded', function () {
  const toggle = document.getElementById('menuToggle');
  const nav = document.getElementById('mainNav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', nav.classList.contains('open') ? 'true' : 'false');
    });
  }
  document.querySelectorAll('.message').forEach(function (message) {
    window.setTimeout(function () { message.style.transition = 'opacity .4s'; message.style.opacity = '0'; }, 6000);
  });
});

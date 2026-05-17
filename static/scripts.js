(function () {
  'use strict';

  // Back-to-top button
  var topBtn = document.querySelector('.back-to-top');
  if (topBtn) {
    var threshold = 400;
    var visible = false;

    var update = function () {
      var shouldShow = window.scrollY > threshold;
      if (shouldShow !== visible) {
        visible = shouldShow;
        topBtn.classList.toggle('back-to-top--visible', shouldShow);
      }
    };

    window.addEventListener('scroll', update, { passive: true });
    update();

    topBtn.addEventListener('click', function (e) {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // Cookie modal
  var modal = document.querySelector('#cookie-modal');
  var openBtn = document.querySelector('[data-open-cookie-modal]');
  var closeBtn = document.querySelector('[data-close-cookie-modal]');

  if (modal && openBtn && typeof modal.showModal === 'function') {
    openBtn.addEventListener('click', function () {
      modal.showModal();
    });

    if (closeBtn) {
      closeBtn.addEventListener('click', function () {
        modal.close();
      });
    }

    // Close when clicking on the backdrop (outside the modal box)
    modal.addEventListener('click', function (e) {
      if (e.target === modal) {
        modal.close();
      }
    });
  }
})();

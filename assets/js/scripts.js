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

    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    var skipLink = document.querySelector('.skip-link');

    topBtn.addEventListener('click', function (e) {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: reduceMotion.matches ? 'auto' : 'smooth' });
      // The button hides itself at the top: move focus there too, so keyboard
      // users are not left on an invisible element
      if (skipLink) skipLink.focus({ preventScroll: true });
    });
  }

  // Cookie modal
  var modal = document.querySelector('#cookie-modal');
  var openBtns = document.querySelectorAll('[data-open-cookie-modal]');
  var closeBtn = document.querySelector('[data-close-cookie-modal]');

  if (modal && openBtns.length && typeof modal.showModal === 'function') {
    openBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        modal.showModal();
      });
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

  // Floating cookie badge. In the empty side margin of wide screens it never
  // covers the text, so it stays. On narrower screens it steps aside while the
  // reader scrolls down, and comes back when scrolling up or near the top.
  // It is hidden whenever the footer, which has the same button, is in view.
  var badge = document.querySelector('.cookie-badge');
  if (badge) {
    var roomy = window.matchMedia('(min-width: 80.5rem)');
    var footer = document.querySelector('footer');
    var footerInView = false;
    var badgeHidden = false;
    var lastY = window.scrollY;

    var updateBadge = function () {
      var y = window.scrollY;
      var delta = y - lastY;
      var hide = footerInView;
      if (!hide && !roomy.matches && y > 200) {
        if (delta > 4) hide = true;               // scrolling down: keep the text clear
        else if (delta >= -4) hide = badgeHidden; // tiny movement: keep the current state
      }
      if (document.activeElement === badge) hide = false; // never hide it under the focus
      lastY = y;
      if (hide !== badgeHidden) {
        badgeHidden = hide;
        badge.classList.toggle('cookie-badge--hidden', hide);
      }
    };

    if (footer && 'IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        footerInView = entries[0].isIntersecting;
        updateBadge();
      }).observe(footer);
    }

    var badgeQueued = false;
    window.addEventListener('scroll', function () {
      if (badgeQueued) return;
      badgeQueued = true;
      window.requestAnimationFrame(function () { badgeQueued = false; updateBadge(); });
    }, { passive: true });
    roomy.addEventListener('change', updateBadge);
  }

  // People carousel (layouts/shortcodes/people.html): dots and arrows only
  // move the native scroller, so touch, trackpad and keyboard keep working.
  document.querySelectorAll('.people').forEach(function (root) {
    var track = root.querySelector('.people-track');
    var slides = root.querySelectorAll('.people-slide');
    var dots = root.querySelectorAll('.people-dot');
    var prev = root.querySelector('.people-arrow[data-dir="-1"]');
    var next = root.querySelector('.people-arrow[data-dir="1"]');
    if (!track || slides.length < 2) return;
    root.querySelector('.people-controls').hidden = false;

    var current = 0;
    var offset = function (i) { return slides[i].offsetLeft - slides[0].offsetLeft; };
    var go = function (i) { track.scrollTo({ left: offset(Math.max(0, Math.min(slides.length - 1, i))) }); };

    var update = function () {
      var x = track.scrollLeft;
      var best = 0;
      slides.forEach(function (s, i) {
        if (Math.abs(offset(i) - x) < Math.abs(offset(best) - x)) best = i;
      });
      if (x + track.clientWidth >= track.scrollWidth - 2) best = slides.length - 1;
      current = best;
      dots.forEach(function (d, i) {
        if (i === best) d.setAttribute('aria-current', 'true');
        else d.removeAttribute('aria-current');
      });
      prev.disabled = best === 0;
      next.disabled = best === slides.length - 1;
      root.classList.toggle('people--end', best === slides.length - 1);
      slides.forEach(function (s, i) { s.classList.toggle('is-current', i === best); });
      document.dispatchEvent(new CustomEvent('people:change'));
    };

    dots.forEach(function (d) {
      d.addEventListener('click', function () { go(Number(d.getAttribute('data-slide'))); });
    });
    prev.addEventListener('click', function () { go(current - 1); });

    // A link to a person (table of contents, #name in the URL) brings that
    // person into view in the carousel too, not only the section
    var slideOf = function (id) {
      var el = id && document.getElementById(id);
      var slide = el && el.closest('.people-slide');
      return slide ? Array.prototype.indexOf.call(slides, slide) : -1;
    };
    var showHash = function () {
      var i = slideOf(decodeURIComponent(window.location.hash.slice(1)));
      if (i >= 0) go(i);
    };
    window.addEventListener('hashchange', showHash);
    document.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('a[href^="#"]');
      var i = a ? slideOf(decodeURIComponent(a.hash.slice(1))) : -1;
      // After the browser's own jump (same hash clicked twice fires no hashchange)
      if (i >= 0) window.setTimeout(function () { go(i); }, 0);
    });
    next.addEventListener('click', function () { go(current + 1); });

    var queued = false;
    track.addEventListener('scroll', function () {
      if (queued) return;
      queued = true;
      window.requestAnimationFrame(function () { queued = false; update(); });
    }, { passive: true });
    update();
    showHash();
  });

  // Mobile nav menu (hamburger)
  var navMenu = document.querySelector('#nav-menu');
  var navOpenBtn = document.querySelector('[data-open-nav-menu]');

  if (navMenu && navOpenBtn && typeof navMenu.showModal === 'function') {
    var setExpanded = function (value) {
      navOpenBtn.setAttribute('aria-expanded', value ? 'true' : 'false');
    };

    navOpenBtn.addEventListener('click', function () {
      navMenu.showModal();
      setExpanded(true);
    });

    // Any element with data-close-nav-menu inside the dialog closes it
    // (close button, logo, and every menu link so navigating also dismisses the dialog)
    navMenu.querySelectorAll('[data-close-nav-menu]').forEach(function (el) {
      el.addEventListener('click', function () {
        navMenu.close();
      });
    });

    // Click on the backdrop (outside the dialog content) closes it
    navMenu.addEventListener('click', function (e) {
      if (e.target === navMenu) {
        navMenu.close();
      }
    });

    // Reset aria-expanded after close (covers ESC, backdrop, link click)
    navMenu.addEventListener('close', function () {
      setExpanded(false);
    });
  }

  // Contact form: build a mailto URL with prefilled subject and body, then open it
  var contactForm = document.querySelector('.contact-form');
  if (contactForm) {
    var fallbackRecipient = contactForm.getAttribute('data-fallback-recipient') || 'info@openinnova.it';
    var isEnglish = (document.documentElement.lang || '').toLowerCase().indexOf('en') === 0;

    var i18n = isEnglish ? {
      greeting: 'Hello,',
      intro: function (name, topic) {
        return 'I\'m writing through the contact form on openinnova.it regarding "' + topic + '".';
      },
      contactsHeader: 'My details:',
      labelName: 'Name',
      labelEmail: 'Email',
      labelPhone: 'Phone',
      signoff: 'Best regards,',
      subjectPrefix: function (topic, name) {
        var who = name || 'a visitor';
        return '[' + topic + '] Request from ' + who + ' — openinnova.it';
      }
    } : {
      greeting: 'Buongiorno,',
      intro: function (name, topic) {
        return 'vi scrivo tramite il modulo di contatto di openinnova.it in merito a "' + topic + '".';
      },
      contactsHeader: 'I miei recapiti:',
      labelName: 'Nome',
      labelEmail: 'Email',
      labelPhone: 'Telefono',
      signoff: 'Cordiali saluti,',
      subjectPrefix: function (topic, name) {
        var who = name || 'un visitatore';
        return '[' + topic + '] Richiesta da ' + who + ' — openinnova.it';
      }
    };

    var submitButton = contactForm.querySelector('button[type="submit"]');
    if (submitButton) submitButton.disabled = false;

    contactForm.addEventListener('submit', function (e) {
      e.preventDefault();

      var name = ((document.getElementById('contact-name') || {}).value || '').trim();
      var email = ((document.getElementById('contact-email') || {}).value || '').trim();
      var phone = ((document.getElementById('contact-phone') || {}).value || '').trim();
      var message = ((document.getElementById('contact-message') || {}).value || '').trim();

      var topicSelect = document.getElementById('contact-topic');
      var selectedOption = topicSelect ? topicSelect.options[topicSelect.selectedIndex] : null;
      var recipient = (selectedOption && selectedOption.getAttribute('data-recipient')) || fallbackRecipient;
      var topicLabel = selectedOption ? selectedOption.textContent.trim() : '';

      var subject = i18n.subjectPrefix(topicLabel, name);

      var lines = [];
      lines.push(i18n.greeting);
      lines.push('');
      lines.push(i18n.intro(name, topicLabel));
      lines.push('');
      lines.push(i18n.contactsHeader);
      lines.push('· ' + i18n.labelName + ': ' + (name || '___'));
      lines.push('· ' + i18n.labelEmail + ': ' + (email || '___'));
      if (phone) lines.push('· ' + i18n.labelPhone + ': ' + phone);
      lines.push('');
      lines.push(message);
      lines.push('');
      lines.push(i18n.signoff);
      lines.push(name);

      var url = 'mailto:' + recipient
        + '?subject=' + encodeURIComponent(subject)
        + '&body=' + encodeURIComponent(lines.join('\n'));

      window.location.href = url;
    });
  }

  // Table of contents: closed in the HTML (nothing shifts on small screens),
  // opened as a sidebar on wide screens. The breakpoint matches style.css.
  var tocDetails = document.querySelector('.toc-details');
  if (tocDetails) {
    var wide = window.matchMedia('(min-width: 68.75rem)');
    var syncToc = function () { tocDetails.open = wide.matches; };
    syncToc();
    wide.addEventListener('change', syncToc);

    // Mark the section being read with aria-current (bar + bold in CSS)
    var tocLinks = {};
    tocDetails.querySelectorAll('a[href^="#"]').forEach(function (a) {
      tocLinks[decodeURIComponent(a.hash.slice(1))] = a;
    });
    var headings = Array.prototype.filter.call(
      document.querySelectorAll('.page-body h2[id], .page-body h3[id]'),
      function (h) { return tocLinks[h.id]; }
    );

    if (headings.length) {
      var currentId = null;
      var setCurrent = function (id) {
        if (id === currentId) return;
        if (currentId) tocLinks[currentId].removeAttribute('aria-current');
        currentId = id;
        if (id) tocLinks[id].setAttribute('aria-current', 'true');
      };

      var updateToc = function () {
        var line = window.innerHeight * 0.3;
        var atEnd = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2;
        var id = null;
        headings.forEach(function (h) {
          var slide = h.closest('.people-slide');
          if (slide && !slide.classList.contains('is-current')) return;
          if (h.getBoundingClientRect().top <= line) id = h.id;
        });
        setCurrent(atEnd ? headings[headings.length - 1].id : id);
      };

      var queued = false;
      window.addEventListener('scroll', function () {
        if (queued) return;
        queued = true;
        window.requestAnimationFrame(function () { queued = false; updateToc(); });
      }, { passive: true });
      document.addEventListener('people:change', updateToc);
      updateToc();
    }
  }
})();

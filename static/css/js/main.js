/* ═══════════════════════════════════════════════════
   QUEUEFLOW — MAIN JAVASCRIPT
   3D Canvas + Animations + Live Updates + Toasts
═══════════════════════════════════════════════════ */

'use strict';

/* ═══════════════════════════════════════════════════
   1. 3D PARTICLE CANVAS BACKGROUND
═══════════════════════════════════════════════════ */

(function initCanvas() {
    var canvas = document.getElementById('bg-canvas');
    if (!canvas) return;

    var ctx = canvas.getContext('2d');
    var W, H;
    var mouseX = 0;
    var mouseY = 0;
    var particles = [];
    var animFrame;

    /* ── Resize ── */
    function resize() {
        W = canvas.width = window.innerWidth;
        H = canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    /* ── Mouse tracking ── */
    window.addEventListener('mousemove', function(e) {
        mouseX = e.clientX;
        mouseY = e.clientY;
    });

    /* ── Particle class ── */
    function Particle() {
        this.reset();
    }

    Particle.prototype.reset = function() {
        this.x = Math.random() * W;
        this.y = Math.random() * H;
        this.z = Math.random() * 800 + 200;
        this.vx = (Math.random() - 0.5) * 0.4;
        this.vy = (Math.random() - 0.5) * 0.4;
        this.vz = (Math.random() - 0.5) * 0.6;
        this.r = Math.random() * 2 + 0.5;
        this.col = Math.random() > 0.5 ? [79, 70, 229] : [6, 182, 212];
    };

    Particle.prototype.update = function() {
        this.x += this.vx + (mouseX - W / 2) * 0.00006;
        this.y += this.vy + (mouseY - H / 2) * 0.00006;
        this.z -= 0.5;
        if (
            this.z < 1 ||
            this.x < -50 || this.x > W + 50 ||
            this.y < -50 || this.y > H + 50
        ) {
            this.reset();
        }
    };

    Particle.prototype.draw = function() {
        var scale = 600 / this.z;
        var sx = (this.x - W / 2) * scale + W / 2;
        var sy = (this.y - H / 2) * scale + H / 2;
        var sr = this.r * scale;
        if (sx < 0 || sx > W || sy < 0 || sy > H || sr < 0.1) return;
        var alpha = Math.min(1, (800 - this.z) / 600) * 0.65;
        ctx.beginPath();
        ctx.arc(sx, sy, sr, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(' + this.col.join(',') + ',' + alpha + ')';
        ctx.fill();
    };

    /* ── Create particles ── */
    for (var i = 0; i < 130; i++) {
        particles.push(new Particle());
    }

    /* ── Grid lines ── */
    function drawGrid() {
        ctx.strokeStyle = 'rgba(79,70,229,0.025)';
        ctx.lineWidth = 1;
        var spacing = 90;
        var x, y;
        for (x = 0; x < W; x += spacing) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, H);
            ctx.stroke();
        }
        for (y = 0; y < H; y += spacing) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(W, y);
            ctx.stroke();
        }
    }

    /* ── Connect nearby particles ── */
    function drawConnections() {
        var i, j, a, b, scaleA, scaleB, ax, ay, bx, by, d;
        for (i = 0; i < particles.length; i++) {
            for (j = i + 1; j < particles.length; j++) {
                a = particles[i];
                b = particles[j];
                scaleA = 600 / a.z;
                scaleB = 600 / b.z;
                ax = (a.x - W / 2) * scaleA + W / 2;
                ay = (a.y - H / 2) * scaleA + H / 2;
                bx = (b.x - W / 2) * scaleB + W / 2;
                by = (b.y - H / 2) * scaleB + H / 2;
                d = Math.sqrt(
                    (ax - bx) * (ax - bx) + (ay - by) * (ay - by)
                );
                if (d < 90) {
                    ctx.beginPath();
                    ctx.moveTo(ax, ay);
                    ctx.lineTo(bx, by);
                    ctx.strokeStyle = 'rgba(79,70,229,' +
                        ((1 - d / 90) * 0.12) + ')';
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                }
            }
        }
    }

    /* ── Render loop ── */
    function loop() {
        ctx.clearRect(0, 0, W, H);
        drawGrid();
        drawConnections();
        for (var i = 0; i < particles.length; i++) {
            particles[i].update();
            particles[i].draw();
        }
        animFrame = requestAnimationFrame(loop);
    }

    loop();
})();


/* ═══════════════════════════════════════════════════
   2. TOAST NOTIFICATIONS
═══════════════════════════════════════════════════ */

function showToast(icon, title, msg, borderColor) {
    var container = document.getElementById('toasts');
    if (!container) return;

    var toast = document.createElement('div');
    toast.className = 'toast';
    toast.style.borderLeft = '3px solid ' + (borderColor || '#4f46e5');

    toast.innerHTML =
        '<div class="toast-icon">' + icon + '</div>' +
        '<div>' +
        '<div class="toast-title">' + title + '</div>' +
        '<div class="toast-msg">' + msg + '</div>' +
        '</div>';

    container.appendChild(toast);

    setTimeout(function() {
        toast.classList.add('out');
        setTimeout(function() {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 400);
    }, 3500);
}


/* ═══════════════════════════════════════════════════
   3. COUNTER ANIMATION
═══════════════════════════════════════════════════ */

function animateCounter(el, target, duration) {
    if (!el) return;
    var start = 0;
    var startTime = null;
    var numTarget = parseInt(target, 10);

    function step(timestamp) {
        if (!startTime) startTime = timestamp;
        var progress = Math.min(
            (timestamp - startTime) / duration, 1
        );
        var eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.floor(eased * numTarget);
        if (progress < 1) {
            requestAnimationFrame(step);
        } else {
            el.textContent = numTarget;
        }
    }
    requestAnimationFrame(step);
}

/* Run counters on landing page */
(function runCounters() {
    var els = document.querySelectorAll('[data-count]');
    if (!els.length) return;
    els.forEach(function(el) {
        var target = el.getAttribute('data-count');
        animateCounter(el, target, 2000);
    });
})();


/* ═══════════════════════════════════════════════════
   4. STAT CARD 3D TILT ON HOVER
═══════════════════════════════════════════════════ */

(function initCardTilt() {
    var cards = document.querySelectorAll('.stat-card');
    cards.forEach(function(card) {

        card.addEventListener('mousemove', function(e) {
            var rect = card.getBoundingClientRect();
            var cx = rect.left + rect.width / 2;
            var cy = rect.top + rect.height / 2;
            var dx = (e.clientX - cx) / (rect.width / 2);
            var dy = (e.clientY - cy) / (rect.height / 2);
            var rotX = -dy * 10;
            var rotY = dx * 10;
            card.style.transform =
                'translateY(-6px) rotateX(' + rotX +
                'deg) rotateY(' + rotY + 'deg)';
        });

        card.addEventListener('mouseleave', function() {
            card.style.transform = '';
            card.style.transition = 'transform 0.5s ease';
            setTimeout(function() {
                card.style.transition = '';
            }, 500);
        });

        card.addEventListener('click', function() {
            card.style.transform = 'scale(0.96)';
            setTimeout(function() {
                card.style.transform = '';
            }, 180);
        });
    });
})();


/* ═══════════════════════════════════════════════════
   5. DEPT PICK BUTTON 3D HOVER
═══════════════════════════════════════════════════ */

(function initDeptCards() {
    var btns = document.querySelectorAll('.dept-pick-btn');
    btns.forEach(function(btn) {
        btn.addEventListener('mousemove', function(e) {
            if (btn.disabled) return;
            var rect = btn.getBoundingClientRect();
            var cx = rect.left + rect.width / 2;
            var cy = rect.top + rect.height / 2;
            var dx = (e.clientX - cx) / (rect.width / 2);
            var dy = (e.clientY - cy) / (rect.height / 2);
            btn.style.transform =
                'translateY(-5px) rotateX(' + (-dy * 8) +
                'deg) rotateY(' + (dx * 8) + 'deg)';
        });
        btn.addEventListener('mouseleave', function() {
            btn.style.transform = '';
        });
    });
})();


/* ═══════════════════════════════════════════════════
   6. FEAT CARD HOVER (LANDING)
═══════════════════════════════════════════════════ */

(function initFeatCards() {
    var cards = document.querySelectorAll('.feat-card');
    cards.forEach(function(card) {
        card.addEventListener('mousemove', function(e) {
            var rect = card.getBoundingClientRect();
            var cx = rect.left + rect.width / 2;
            var cy = rect.top + rect.height / 2;
            var dx = (e.clientX - cx) / (rect.width / 2);
            var dy = (e.clientY - cy) / (rect.height / 2);
            card.style.transform =
                'translateY(-6px) rotateX(' + (-dy * 6) +
                'deg) rotateY(' + (dx * 6) + 'deg)';
        });
        card.addEventListener('mouseleave', function() {
            card.style.transform = '';
        });
    });
})();


/* ═══════════════════════════════════════════════════
   7. NAVBAR SCROLL EFFECT (LANDING)
═══════════════════════════════════════════════════ */

(function initNavbar() {
    var navbar = document.querySelector('.navbar');
    if (!navbar) return;

    window.addEventListener('scroll', function() {
        if (window.scrollY > 40) {
            navbar.style.background = 'rgba(10,14,26,0.96)';
            navbar.style.borderColor = 'rgba(255,255,255,0.12)';
        } else {
            navbar.style.background = 'rgba(10,14,26,0.70)';
            navbar.style.borderColor = 'rgba(255,255,255,0.09)';
        }
    });
})();


/* ═══════════════════════════════════════════════════
   8. SMOOTH SCROLL FOR NAV LINKS (LANDING)
═══════════════════════════════════════════════════ */

(function initSmoothScroll() {
    var links = document.querySelectorAll('a[href^="#"]');
    links.forEach(function(link) {
        link.addEventListener('click', function(e) {
            var id = link.getAttribute('href').slice(1);
            var el = document.getElementById(id);
            if (el) {
                e.preventDefault();
                el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
})();


/* ═══════════════════════════════════════════════════
   9. LIVE QUEUE DEPT CARDS (LANDING PAGE)
═══════════════════════════════════════════════════ */

(function initLandingDeptCards() {
    var container = document.getElementById('dept-cards');
    if (!container) return;

    var depts = [
        { name: 'Banking', icon: '🏦', col: '#4f46e5' },
        { name: 'Pharmacy', icon: '💊', col: '#06b6d4' },
        { name: 'Immigration', icon: '🛂', col: '#10b981' },
        { name: 'Medical', icon: '🏥', col: '#f59e0b' }
    ];

    function renderDeptCards(data) {
        container.innerHTML = '';
        depts.forEach(function(dept, idx) {
            var queueData = data && data[idx] ? data[idx] : null;
            var count = queueData ? queueData.waiting_count : 0;
            var status = queueData ? queueData.status : 'active';

            var card = document.createElement('div');
            card.className = 'dept-live-card';
            card.style.setProperty('--dlc',
                dept.col.replace('#', 'rgba(') + ',0.25)');

            card.innerHTML =
                '<div class="dlc-icon">' + dept.icon + '</div>' +
                '<div class="dlc-name">' + dept.name + '</div>' +
                '<div class="dlc-count" style="color:' + dept.col + '">' +
                count +
                '</div>' +
                '<div class="dlc-label">waiting now</div>' +
                '<br>' +
                '<span class="status-badge s-' + status + '">' +
                status +
                '</span>';

            container.appendChild(card);
        });
    }

    /* Fetch real data */
    function fetchDeptData() {
        fetch('/live-queue')
            .then(function(r) { return r.json(); })
            .then(function(data) { renderDeptCards(data); })
            .catch(function() { renderDeptCards(null); });
    }

    fetchDeptData();
    setInterval(fetchDeptData, 15000);
})();


/* ═══════════════════════════════════════════════════
   10. SIDEBAR MOBILE TOGGLE
═══════════════════════════════════════════════════ */

(function initMobileSidebar() {
    var sidebar = document.getElementById('sidebar');
    if (!sidebar) return;

    /* Create hamburger button */
    var hamburger = document.createElement('button');
    hamburger.id = 'hamburger';
    hamburger.innerHTML = '☰';
    hamburger.style.cssText =
        'position:fixed;top:16px;left:16px;z-index:200;' +
        'background:rgba(79,70,229,0.9);color:#fff;border:none;' +
        'width:40px;height:40px;border-radius:10px;font-size:18px;' +
        'display:none;align-items:center;justify-content:center;' +
        'cursor:pointer;box-shadow:0 4px 16px rgba(79,70,229,0.4);';

    document.body.appendChild(hamburger);

    function checkMobile() {
        if (window.innerWidth <= 768) {
            hamburger.style.display = 'flex';
        } else {
            hamburger.style.display = 'none';
            sidebar.classList.remove('open');
        }
    }

    hamburger.addEventListener('click', function() {
        sidebar.classList.toggle('open');
    });

    /* Close on outside click */
    document.addEventListener('click', function(e) {
        if (
            sidebar.classList.contains('open') &&
            !sidebar.contains(e.target) &&
            e.target !== hamburger
        ) {
            sidebar.classList.remove('open');
        }
    });

    checkMobile();
    window.addEventListener('resize', checkMobile);
})();


/* ═══════════════════════════════════════════════════
   11. PAGE LOAD ANIMATIONS (STAGGERED)
═══════════════════════════════════════════════════ */

(function initPageAnimations() {
    var style = document.createElement('style');
    style.textContent =
        '@keyframes fadeSlideUp {' +
        'from { opacity:0; transform:translateY(24px); }' +
        'to   { opacity:1; transform:translateY(0); }' +
        '}' +
        '.stat-card    { animation: fadeSlideUp 0.5s ease both; }' +
        '.section-card { animation: fadeSlideUp 0.5s ease both; }' +
        '.stat-card:nth-child(1) { animation-delay:0.05s; }' +
        '.stat-card:nth-child(2) { animation-delay:0.12s; }' +
        '.stat-card:nth-child(3) { animation-delay:0.19s; }' +
        '.stat-card:nth-child(4) { animation-delay:0.26s; }' +
        '@keyframes fadeRowIn {' +
        'from { opacity:0; transform:translateX(-12px); }' +
        'to   { opacity:1; transform:translateX(0); }' +
        '}';
    document.head.appendChild(style);
})();


/* ═══════════════════════════════════════════════════
   12. TABLE ROW HOVER EFFECTS
═══════════════════════════════════════════════════ */

(function initTableRows() {
    var tables = document.querySelectorAll('.queue-table');
    tables.forEach(function(table) {
        var rows = table.querySelectorAll('tbody tr');
        rows.forEach(function(row, idx) {
            row.style.animation =
                'fadeRowIn 0.4s ease ' + (idx * 0.06) + 's both';

            row.addEventListener('mouseenter', function() {
                row.style.transform = 'translateX(4px)';
                row.style.transition = 'transform 0.2s ease';
            });
            row.addEventListener('mouseleave', function() {
                row.style.transform = '';
            });
        });
    });
})();


/* ═══════════════════════════════════════════════════
   13. DEPT CONTROL CARD TILT (ADMIN)
═══════════════════════════════════════════════════ */

(function initDeptControlCards() {
    var cards = document.querySelectorAll('.dept-control-card');
    cards.forEach(function(card) {
        card.addEventListener('mousemove', function(e) {
            var rect = card.getBoundingClientRect();
            var cx = rect.left + rect.width / 2;
            var cy = rect.top + rect.height / 2;
            var dx = (e.clientX - cx) / (rect.width / 2);
            var dy = (e.clientY - cy) / (rect.height / 2);
            card.style.transform =
                'translateY(-4px) rotateX(' + (-dy * 5) +
                'deg) rotateY(' + (dx * 5) + 'deg)';
        });
        card.addEventListener('mouseleave', function() {
            card.style.transform = '';
        });
    });
})();


/* ═══════════════════════════════════════════════════
   14. BUTTON RIPPLE EFFECT
═══════════════════════════════════════════════════ */

(function initRipple() {
    var rippleStyle = document.createElement('style');
    rippleStyle.textContent =
        '.ripple-effect {' +
        'position:absolute;border-radius:50%;' +
        'background:rgba(255,255,255,0.25);' +
        'transform:scale(0);pointer-events:none;' +
        'animation:rippleAnim 0.55s linear;' +
        '}' +
        '@keyframes rippleAnim {' +
        'to { transform:scale(4); opacity:0; }' +
        '}';
    document.head.appendChild(rippleStyle);

    document.addEventListener('click', function(e) {
        var btn = e.target.closest('.btn');
        if (!btn) return;

        var rect = btn.getBoundingClientRect();
        var size = Math.max(rect.width, rect.height);
        var x = e.clientX - rect.left - size / 2;
        var y = e.clientY - rect.top - size / 2;
        var ripple = document.createElement('span');

        ripple.className = 'ripple-effect';
        ripple.style.cssText =
            'width:' + size + 'px;' +
            'height:' + size + 'px;' +
            'left:' + x + 'px;' +
            'top:' + y + 'px;';

        btn.style.position = 'relative';
        btn.style.overflow = 'hidden';
        btn.appendChild(ripple);

        setTimeout(function() {
            if (ripple.parentNode) {
                ripple.parentNode.removeChild(ripple);
            }
        }, 600);
    });
})();


/* ═══════════════════════════════════════════════════
   15. PROGRESS BAR SHIMMER (USER DASHBOARD)
═══════════════════════════════════════════════════ */

(function initProgressBars() {
    var shimmerStyle = document.createElement('style');
    shimmerStyle.textContent =
        '.progress-track {' +
        'height:8px;background:rgba(255,255,255,0.06);' +
        'border-radius:10px;overflow:hidden;margin-top:10px;' +
        '}' +
        '.progress-fill {' +
        'height:100%;border-radius:10px;' +
        'background:linear-gradient(90deg,#4f46e5,#06b6d4);' +
        'position:relative;transition:width 1s ease;' +
        '}' +
        '.progress-fill::after {' +
        'content:"";position:absolute;inset:0;' +
        'background:linear-gradient(90deg,' +
        'transparent,rgba(255,255,255,0.3),transparent);' +
        'animation:shimmer 2s linear infinite;' +
        '}' +
        '@keyframes shimmer {' +
        '0%   { transform:translateX(-100%); }' +
        '100% { transform:translateX(100%); }' +
        '}';
    document.head.appendChild(shimmerStyle);
})();


/* ═══════════════════════════════════════════════════
   16. SECTION SWITCHER HELPER
═══════════════════════════════════════════════════ */

function showSection(name) {
    /* Update nav */
    var navItems = document.querySelectorAll('.nav-item');
    if (event && event.currentTarget) {
        navItems.forEach(function(n) { n.classList.remove('active'); });
        event.currentTarget.classList.add('active');
    }

    /* Show/hide sections */
    var allSections = document.querySelectorAll('[id^="section-"]');
    allSections.forEach(function(sec) {
        var secName = sec.id.replace('section-', '');
        sec.style.display = (secName === name) ? 'block' : 'none';
    });
}


/* ═══════════════════════════════════════════════════
   17. FORM INPUT FOCUS GLOW
═══════════════════════════════════════════════════ */

(function initInputEffects() {
    var inputs = document.querySelectorAll('.form-input');
    inputs.forEach(function(input) {
        input.addEventListener('focus', function() {
            var wrap = input.closest('.input-wrap');
            if (wrap) {
                wrap.style.filter = 'drop-shadow(0 0 8px rgba(79,70,229,0.3))';
            }
        });
        input.addEventListener('blur', function() {
            var wrap = input.closest('.input-wrap');
            if (wrap) {
                wrap.style.filter = '';
            }
        });
    });
})();


/* ═══════════════════════════════════════════════════
   18. TICKER AUTO-DUPLICATE CHECK
═══════════════════════════════════════════════════ */

(function initTicker() {
    var inner = document.getElementById('ticker-inner');
    if (!inner) return;

    /* Make sure content is duplicated for seamless loop */
    var original = inner.innerHTML;
    if (inner.children.length < 6) {
        inner.innerHTML = original + original;
    }
})();


/* ═══════════════════════════════════════════════════
   19. INTERSECTION OBSERVER — ANIMATE ON SCROLL
═══════════════════════════════════════════════════ */

(function initScrollAnimate() {
    if (!window.IntersectionObserver) return;

    var obsStyle = document.createElement('style');
    obsStyle.textContent =
        '.scroll-hidden {' +
        'opacity:0;transform:translateY(30px);' +
        'transition:opacity 0.6s ease,transform 0.6s ease;' +
        '}' +
        '.scroll-visible {' +
        'opacity:1;transform:translateY(0);' +
        '}';
    document.head.appendChild(obsStyle);

    var targets = document.querySelectorAll(
        '.feat-card, .dept-live-card, .section-card, .stat-card'
    );

    var observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                entry.target.classList.remove('scroll-hidden');
                entry.target.classList.add('scroll-visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12 });

    targets.forEach(function(el) {
        el.classList.add('scroll-hidden');
        observer.observe(el);
    });
})();


/* ═══════════════════════════════════════════════════
   20. QUEUE STATUS BADGE AUTO-REFRESH COLOR
═══════════════════════════════════════════════════ */

(function initBadgePulse() {
    var badgeStyle = document.createElement('style');
    badgeStyle.textContent =
        '.s-serving {' +
        'animation:badgePulse 2s ease-in-out infinite;' +
        '}' +
        '@keyframes badgePulse {' +
        '0%,100% { box-shadow:none; }' +
        '50%      {' +
        'box-shadow:0 0 12px rgba(16,185,129,0.5);' +
        '}' +
        '}';
    document.head.appendChild(badgeStyle);
})();


/* ═══════════════════════════════════════════════════
   21. TOKEN HERO 3D FLOAT (USER DASHBOARD)
═══════════════════════════════════════════════════ */

(function initTokenHeroFloat() {
    var hero = document.querySelector('.token-hero-user');
    if (!hero) return;

    hero.addEventListener('mousemove', function(e) {
        var rect = hero.getBoundingClientRect();
        var cx = rect.left + rect.width / 2;
        var cy = rect.top + rect.height / 2;
        var dx = (e.clientX - cx) / (rect.width / 2);
        var dy = (e.clientY - cy) / (rect.height / 2);
        hero.style.transform =
            'perspective(1000px) rotateX(' + (-dy * 3) +
            'deg) rotateY(' + (dx * 3) + 'deg)';
    });
    hero.addEventListener('mouseleave', function() {
        hero.style.transform = '';
        hero.style.transition = 'transform 0.6s ease';
        setTimeout(function() {
            hero.style.transition = '';
        }, 600);
    });
})();


/* ═══════════════════════════════════════════════════
   22. DEPT CONTROL CARD GLOW ON HOVER (ADMIN)
═══════════════════════════════════════════════════ */

(function initDccGlow() {
    var glowColors = [
        'rgba(227, 227, 238, 0.3)',
        'rgba(218, 234, 231, 0.3)',
        'rgba(16,185,129,0.3)',
        'rgba(245,158,11,0.3)'
    ];

    var cards = document.querySelectorAll('.dept-control-card');
    cards.forEach(function(card, idx) {
        var col = glowColors[idx % glowColors.length];
        card.addEventListener('mouseenter', function() {
            card.style.boxShadow = '0 16px 40px ' + col;
        });
        card.addEventListener('mouseleave', function() {
            card.style.boxShadow = '';
        });
    });
})();


/* ═══════════════════════════════════════════════════
   23. WINDOW LOAD — STARTUP TOAST
═══════════════════════════════════════════════════ */

window.addEventListener('load', function() {
    /* Only show on app pages (sidebar present) */
    var sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;

    setTimeout(function() {
        showToast(
            '✅',
            'System Online',
            'QueueFlow connected. Live updates active.',
            '#d1e6df'
        );
    }, 800);
});


/* ═══════════════════════════════════════════════════
   24. KEYBOARD SHORTCUT HINTS
═══════════════════════════════════════════════════ */

(function initKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        /* Escape closes any open modal overlays */
        if (e.key === 'Escape') {
            var overlays = document.querySelectorAll('.modal-overlay.show');
            overlays.forEach(function(o) { o.classList.remove('show'); });
        }
        /* Ctrl+R or Cmd+R — custom queue refresh */
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            /* Let browser handle real reload, just show toast */
        }
    });
})();


/* ═══════════════════════════════════════════════════
   25. UTILITY — DEBOUNCE
═══════════════════════════════════════════════════ */

function debounce(fn, delay) {
    var timer;
    return function() {
        var args = arguments;
        var context = this;
        clearTimeout(timer);
        timer = setTimeout(function() {
            fn.apply(context, args);
        }, delay);
    };
}


/* ═══════════════════════════════════════════════════
   26. SEARCH / FILTER TABLE (ADMIN)
═══════════════════════════════════════════════════ */

(function initTableSearch() {
    var searchBar = document.querySelector('.search-bar');
    if (!searchBar) return;

    var input = document.createElement('input');
    input.type = 'text';
    input.placeholder = 'Filter tokens...';
    input.style.cssText =
        'background:transparent;border:none;outline:none;' +
        'color:#e2e8f0;font-size:13px;width:200px;font-family:inherit;';

    searchBar.innerHTML = '🔍 ';
    searchBar.appendChild(input);

    input.addEventListener('input', debounce(function() {
        var val = input.value.toLowerCase();
        var rows = document.querySelectorAll(
            '#admin-tbody tr, #admin-token-table tbody tr'
        );
        rows.forEach(function(row) {
            var text = row.textContent.toLowerCase();
            row.style.display = text.includes(val) ? '' : 'none';
        });
    }, 200));
})();


/* ═══════════════════════════════════════════════════
   27. AUTO-REFRESH LIVE BADGE COUNT (SIDEBAR)
═══════════════════════════════════════════════════ */

(function initSidebarBadge() {
    var badge = document.getElementById('live-count');
    if (!badge) return;

    function refreshBadge() {
        fetch('/live-queue')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var total = 0;
                data.forEach(function(q) { total += q.waiting_count; });
                badge.textContent = total;
                if (total > 0) {
                    badge.style.background = '#4f46e5';
                } else {
                    badge.style.background = '#c3cbd6';
                }
            })
            .catch(function() {});
    }

    refreshBadge();
    setInterval(refreshBadge, 12000);
})();
this.col = Math.random() > 0.5 ?
    [225, 29, 72] :
    [251, 113, 133];
(() => {
  const navToggle = document.querySelector('.nav-toggle');
  const nav = document.querySelector('.site-nav');

  navToggle?.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', String(open));
  });

  nav?.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
    nav.classList.remove('open');
    navToggle?.setAttribute('aria-expanded', 'false');
  }));

  const locale = document.documentElement.lang === 'en' ? 'en' : 'ar';
  const rtl = document.documentElement.dir === 'rtl';
  const content = {
    ar: {
      next: 'الخطوة التالية',
      restart: 'العودة للبداية',
      steps: [
        { label: 'الخطوة الأولى', title: 'طلب صيانة جديد', description: 'يسجل العميل المركبة ويختار الفرع والخدمة والموعد المناسب.', points: ['تحقق من ملكية المركبة', 'اختيار الفرع والخدمة', 'تأكيد واضح للطلب'], view: 'request', service: 'فحص دوري', status: 'تم استلام الطلب', badge: 'جديد' },
        { label: 'الخطوة الثانية', title: 'فحص موثق وواضح', description: 'يحوّل الفريق نتيجة الفحص إلى خدمات وقطع مقترحة داخل أمر العمل.', points: ['ملاحظات وصور مرتبطة', 'تكلفة ومدة تقديرية', 'منع التغييرات غير المصرح بها'], view: 'inspect', service: 'فحص المركبة', status: 'تم إعداد عرض السعر', badge: 'مراجعة' },
        { label: 'الخطوة الثالثة', title: 'موافقة قبل التنفيذ', description: 'يراجع العميل عرض السعر ويوافق عليه قبل بدء الأعمال الإضافية.', points: ['بنود سعر مفصلة', 'حالة موافقة قابلة للتتبع', 'تنبيه فوري للورشة'], view: 'approve', service: 'عرض سعر رقم Q-1042', status: 'وافق العميل', badge: 'معتمد' },
        { label: 'الخطوة الرابعة', title: 'فاتورة وتسليم منظم', description: 'تُحدّث الفاتورة والمخزون والحالة قبل إشعار العميل بأن المركبة جاهزة.', points: ['خصم المخزون بمعاملة آمنة', 'تسجيل المدفوعات', 'سجل صيانة دائم للمركبة'], view: 'deliver', service: 'الفاتورة INV-1042', status: 'جاهزة للاستلام', badge: 'مكتمل' }
      ]
    },
    en: {
      next: 'Next step',
      restart: 'Back to the beginning',
      steps: [
        { label: 'Step one', title: 'Create a service request', description: 'The customer registers the vehicle and chooses the branch, service, and preferred date.', points: ['Vehicle ownership check', 'Branch and service selection', 'Clear request confirmation'], view: 'request', service: 'Scheduled service', status: 'Request received', badge: 'New' },
        { label: 'Step two', title: 'Document the inspection', description: 'The team turns inspection findings into proposed services and parts inside the work order.', points: ['Linked notes and images', 'Estimated cost and duration', 'Unauthorized changes blocked'], view: 'inspect', service: 'Vehicle inspection', status: 'Quote prepared', badge: 'Review' },
        { label: 'Step three', title: 'Approve before work starts', description: 'The customer reviews the quote and approves it before additional work begins.', points: ['Detailed quote items', 'Traceable approval state', 'Immediate workshop notification'], view: 'approve', service: 'Quote Q-1042', status: 'Customer approved', badge: 'Approved' },
        { label: 'Step four', title: 'Invoice and deliver', description: 'The invoice, stock, and status update before the customer is notified that the vehicle is ready.', points: ['Transactional stock movement', 'Payment recording', 'Permanent vehicle history'], view: 'deliver', service: 'Invoice INV-1042', status: 'Ready to collect', badge: 'Complete' }
      ]
    }
  };

  const strings = content[locale];
  const tabs = [...document.querySelectorAll('.demo-tabs button')];
  const label = document.querySelector('#demo-label');
  const title = document.querySelector('#demo-title');
  const description = document.querySelector('#demo-description');
  const points = document.querySelector('#demo-points');
  const visual = document.querySelector('#demo-visual');
  const recordTitle = visual?.querySelector('.demo-record strong');
  const recordStatus = visual?.querySelector('.demo-record small');
  const recordBadge = visual?.querySelector('.demo-record b');
  const next = document.querySelector('.demo-next');
  let active = 0;

  function setStep(index, focus = false) {
    active = (index + strings.steps.length) % strings.steps.length;
    const step = strings.steps[active];
    tabs.forEach((tab, tabIndex) => {
      const selected = tabIndex === active;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    label.textContent = step.label;
    title.textContent = step.title;
    description.textContent = step.description;
    points.replaceChildren(...step.points.map((text) => {
      const item = document.createElement('li');
      item.textContent = text;
      return item;
    }));
    visual.dataset.view = step.view;
    recordTitle.textContent = step.service;
    recordStatus.textContent = step.status;
    recordBadge.textContent = step.badge;
    next.textContent = active === strings.steps.length - 1 ? strings.restart : strings.next;
    if (focus) tabs[active].focus();
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => setStep(index));
    tab.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        setStep(active + (rtl ? 1 : -1), true);
      }
      if (event.key === 'ArrowRight') {
        event.preventDefault();
        setStep(active + (rtl ? -1 : 1), true);
      }
    });
  });

  next?.addEventListener('click', () => setStep(active + 1));

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const reveals = document.querySelectorAll('.reveal');
  if (reducedMotion || !('IntersectionObserver' in window)) {
    reveals.forEach((element) => element.classList.add('visible'));
  } else {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    reveals.forEach((element) => observer.observe(element));
  }

  document.querySelector('#year').textContent = new Date().getFullYear();
  document.querySelector('#demo-panel')?.setAttribute('aria-labelledby', 'demo-title');
})();

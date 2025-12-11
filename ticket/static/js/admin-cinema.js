// Добавить в конец файла admin-cinema.js:

// Функции для улучшения админ-интерфейса
document.addEventListener('DOMContentLoaded', function() {
    console.log('Admin cinema improvements loaded');

    // 1. Исправление выравнивания в выпадающих списках
    const fixSelectAlignment = () => {
        document.querySelectorAll('select').forEach(select => {
            // Убеждаемся что у select есть правильная высота
            if (select.offsetHeight < 36) {
                select.style.height = '38px';
                select.style.lineHeight = '38px';
                select.style.paddingTop = '0';
                select.style.paddingBottom = '0';
            }

            // Добавляем стрелочку если её нет
            if (!select.style.backgroundImage || select.style.backgroundImage === 'none') {
                select.style.backgroundImage = "url('data:image/svg+xml;charset=UTF-8,%3csvg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"%23ffcc00\"%3e%3cpath d=\"M7 10l5 5 5-5z\"/%3e%3c/svg%3e')";
                select.style.backgroundRepeat = 'no-repeat';
                select.style.backgroundPosition = 'right 12px center';
                select.style.backgroundSize = '16px';
                select.style.paddingRight = '40px';
            }
        });
    };

    // 2. Автоматический подбор ширины для поля поиска
    const adjustSearchField = () => {
        const searchInput = document.querySelector('#searchbar');
        const searchButton = document.querySelector('#changelist-search button[type="submit"]');

        if (searchInput && searchButton) {
            // На мобильных делаем ширину 100%
            if (window.innerWidth < 768) {
                searchInput.style.width = '100%';
                searchButton.style.width = '100%';
            } else {
                // На десктопе делаем пропорциональные размеры
                const container = searchInput.parentElement;
                if (container && container.offsetWidth > 400) {
                    searchInput.style.width = 'calc(100% - 130px)';
                    searchButton.style.width = '120px';
                }
            }
        }
    };

    // 3. Индикатор горизонтальной прокрутки для таблиц
    const addScrollIndicator = () => {
        const tables = document.querySelectorAll('#result_list');
        tables.forEach(table => {
            if (table.scrollWidth > table.clientWidth) {
                const container = table.closest('.results');
                if (container && !container.classList.contains('has-scroll-indicator')) {
                    container.classList.add('has-scroll-indicator');

                    // Добавляем подсказку о прокрутке
                    const hint = document.createElement('div');
                    hint.style.cssText = `
                        position: absolute;
                        bottom: 5px;
                        right: 5px;
                        background: rgba(255, 0, 0, 0.7);
                        color: #ffcc00;
                        padding: 4px 8px;
                        border-radius: 4px;
                        font-size: 11px;
                        font-weight: bold;
                        z-index: 10;
                        pointer-events: none;
                        opacity: 0.8;
                    `;
                    hint.textContent = '← прокрутка →';
                    container.style.position = 'relative';
                    container.appendChild(hint);
                }
            }
        });
    };

    // 4. Выравнивание выпадающих списков в отчетах
    const fixReportFilters = () => {
        const reportSelects = document.querySelectorAll('.report-filters select');
        reportSelects.forEach(select => {
            select.style.height = '38px';
            select.style.lineHeight = '38px';
            select.style.minWidth = '200px';

            // Добавляем класс для стилизации
            if (!select.classList.contains('report-select')) {
                select.classList.add('report-select');
            }
        });

        // Выравниваем лейблы
        const labels = document.querySelectorAll('.report-filters label');
        labels.forEach(label => {
            label.style.display = 'flex';
            label.style.alignItems = 'center';
            label.style.justifyContent = 'flex-end';
            label.style.minHeight = '38px';
        });
    };

    // 5. Улучшение кнопок
    const enhanceButtons = () => {
        document.querySelectorAll('.button, input[type="submit"], input[type="button"], .btn').forEach(btn => {
            // Убеждаемся что текст виден
            btn.style.display = 'inline-flex';
            btn.style.alignItems = 'center';
            btn.style.justifyContent = 'center';
            btn.style.height = '38px';
            btn.style.lineHeight = '1';
            btn.style.verticalAlign = 'middle';
            btn.style.padding = '0 20px';

            // Добавляем эффект наведения
            if (!btn.hasAttribute('data-enhanced')) {
                btn.setAttribute('data-enhanced', 'true');

                btn.addEventListener('mouseenter', function() {
                    this.style.transform = 'translateY(-2px)';
                    this.style.transition = 'all 0.3s ease';
                });

                btn.addEventListener('mouseleave', function() {
                    this.style.transform = 'translateY(0)';
                });
            }
        });
    };

    // Инициализация всех функций
    fixSelectAlignment();
    adjustSearchField();
    addScrollIndicator();
    fixReportFilters();
    enhanceButtons();

    // Обновляем при изменении размера окна
    window.addEventListener('resize', function() {
        setTimeout(() => {
            fixSelectAlignment();
            adjustSearchField();
            addScrollIndicator();
        }, 100);
    });

    // Обновляем при динамическом изменении DOM (например, после AJAX)
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length) {
                setTimeout(() => {
                    fixSelectAlignment();
                    adjustSearchField();
                    addScrollIndicator();
                    fixReportFilters();
                    enhanceButtons();
                }, 300);
            }
        });
    });

    // Начинаем наблюдение
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    console.log('Admin improvements applied successfully');
});
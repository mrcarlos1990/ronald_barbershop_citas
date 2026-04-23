document.addEventListener("DOMContentLoaded", () => {
    initPageLoader();
    initSidebarToggle();
    initConfirmActions();
    initImagePreviews();
    initPasswordConfirmation();
    initRevealAnimations();
    initCountUp();
    document.querySelectorAll("form[data-availability-url]").forEach(initBookingExperience);
});

function initPageLoader() {
    const loader = document.querySelector("#page-loader");
    if (!loader) {
        return;
    }

    requestAnimationFrame(() => {
        loader.classList.add("is-hidden");
    });
}

function initSidebarToggle() {
    const toggle = document.querySelector("[data-sidebar-toggle]");
    if (!toggle) {
        return;
    }

    const key = "ronald-admin-sidebar-collapsed";
    const body = document.body;

    if (window.localStorage.getItem(key) === "1" && window.innerWidth > 1080) {
        body.classList.add("sidebar-collapsed");
    }

    window.addEventListener("resize", () => {
        if (window.innerWidth <= 1080) {
            body.classList.remove("sidebar-collapsed");
        }
    });

    toggle.addEventListener("click", () => {
        if (window.innerWidth <= 1080) {
            body.classList.remove("sidebar-collapsed");
            return;
        }
        body.classList.toggle("sidebar-collapsed");
        window.localStorage.setItem(key, body.classList.contains("sidebar-collapsed") ? "1" : "0");
    });
}

function initConfirmActions() {
    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const message = form.dataset.confirm || "Deseas continuar con esta accion?";
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });
}

function initImagePreviews() {
    document.querySelectorAll('input[type="file"][data-preview-target]').forEach((input) => {
        input.addEventListener("change", () => {
            const targetId = input.dataset.previewTarget;
            const target = document.getElementById(targetId);
            const file = input.files && input.files[0];

            if (!target || !file) {
                return;
            }

            const reader = new FileReader();
            reader.addEventListener("load", (event) => {
                const markup = `<img src="${event.target?.result || ""}" alt="Vista previa">`;
                if (target.tagName === "IMG") {
                    target.src = String(event.target?.result || "");
                } else {
                    target.innerHTML = markup;
                    target.classList.remove("image-placeholder");
                }
            });
            reader.readAsDataURL(file);
        });
    });
}

function initPasswordConfirmation() {
    document.querySelectorAll("form").forEach((form) => {
        const passwordInput = form.querySelector('input[name="password"]');
        const confirmInput = form.querySelector('input[name="confirm_password"]');

        if (!passwordInput || !confirmInput) {
            return;
        }

        const validate = () => {
            if (confirmInput.value && passwordInput.value !== confirmInput.value) {
                confirmInput.setCustomValidity("Las contrasenas no coinciden.");
            } else {
                confirmInput.setCustomValidity("");
            }
        };

        passwordInput.addEventListener("input", validate);
        confirmInput.addEventListener("input", validate);
        form.addEventListener("submit", validate);
    });
}

function initRevealAnimations() {
    const nodes = document.querySelectorAll("[data-reveal]");
    if (!nodes.length || !("IntersectionObserver" in window)) {
        nodes.forEach((node) => node.classList.add("is-visible"));
        return;
    }

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-visible");
                    observer.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.16 }
    );

    nodes.forEach((node) => observer.observe(node));
}

function initCountUp() {
    const counters = document.querySelectorAll("[data-countup]");
    if (!counters.length) {
        return;
    }

    const animateCounter = (element) => {
        const target = Number(element.dataset.countup || 0);
        if (Number.isNaN(target)) {
            return;
        }

        const duration = 850;
        const startTime = performance.now();

        const frame = (now) => {
            const progress = Math.min((now - startTime) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            element.textContent = Math.round(target * eased).toLocaleString("es-DO");
            if (progress < 1) {
                requestAnimationFrame(frame);
            }
        };

        requestAnimationFrame(frame);
    };

    if (!("IntersectionObserver" in window)) {
        counters.forEach(animateCounter);
        return;
    }

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.4 }
    );

    counters.forEach((counter) => observer.observe(counter));
}

function initBookingExperience(form) {
    const serviceInput = form.querySelector("#servicio_id");
    const barberInput = form.querySelector("#barbero_id");
    const dateInput = form.querySelector("#fecha");
    const timeInput = form.querySelector("#hora");
    const phoneInput = form.querySelector("#telefono");
    const feedback = form.querySelector("#availability-feedback");
    const slotsContainer = form.querySelector("#slots-container");
    const calendarWidget = form.querySelector(".calendar-widget");
    const selectedDateLabel = form.querySelector("#selected-date-label");

    if (!serviceInput || !dateInput || !timeInput || !feedback || !slotsContainer) {
        return;
    }

    const availabilityUrl = form.dataset.availabilityUrl;
    const calendarUrl = form.dataset.calendarUrl;
    const excludeAppointmentId = form.dataset.excludeAppointmentId;
    let currentMonth = calendarWidget?.dataset.initialMonth || toMonthValue(new Date());
    let selectedDate = dateInput.value || "";

    const setFeedback = (message, isError = false) => {
        feedback.textContent = message;
        feedback.classList.toggle("is-error", isError);
    };

    const updateSelectedDateLabel = () => {
        if (!selectedDateLabel) {
            return;
        }

        if (!selectedDate) {
            selectedDateLabel.textContent = "Selecciona un dia en el calendario";
            return;
        }

        const parsed = new Date(`${selectedDate}T12:00:00`);
        selectedDateLabel.textContent = new Intl.DateTimeFormat("es-DO", {
            weekday: "long",
            day: "numeric",
            month: "long",
            year: "numeric",
        }).format(parsed);
    };

    const selectSlot = (button) => {
        slotsContainer.querySelectorAll(".slot-button").forEach((item) => item.classList.remove("is-selected"));
        button.classList.add("is-selected");
        timeInput.value = button.dataset.value;
        setFeedback(`Horario seleccionado: ${button.dataset.label}`);
    };

    const renderSlots = (slots) => {
        const currentValue = timeInput.value || form.dataset.selectedTime || "";
        slotsContainer.innerHTML = "";

        if (!slots.length) {
            timeInput.value = "";
            setFeedback("No hay horarios disponibles para esa seleccion.", true);
            return;
        }

        setFeedback("Selecciona uno de los horarios disponibles.");

        slots.forEach((slot) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "slot-button";
            button.dataset.value = slot.value;
            button.dataset.label = slot.label;
            button.innerHTML = `
                <span>${slot.label}</span>
                <small>${barberInput && barberInput.value ? "Disponible" : slot.barber_name}</small>
            `;
            button.addEventListener("click", () => selectSlot(button));

            if (slot.value === currentValue) {
                button.classList.add("is-selected");
                timeInput.value = slot.value;
                setFeedback(`Horario seleccionado: ${slot.label}`);
            }

            slotsContainer.appendChild(button);
        });

        if (currentValue && !slots.some((slot) => slot.value === currentValue)) {
            timeInput.value = "";
        }
    };

    const loadSlots = async () => {
        if (!serviceInput.value || !dateInput.value) {
            slotsContainer.innerHTML = "";
            timeInput.value = "";
            setFeedback("Selecciona servicio y fecha para consultar la disponibilidad.");
            return;
        }

        setFeedback("Consultando horarios disponibles...");

        const params = new URLSearchParams({
            service_id: serviceInput.value,
            date: dateInput.value,
        });

        if (barberInput && barberInput.value) {
            params.set("barber_id", barberInput.value);
        }

        if (excludeAppointmentId) {
            params.set("exclude_appointment_id", excludeAppointmentId);
        }

        try {
            const response = await fetch(`${availabilityUrl}?${params.toString()}`);
            const data = await response.json();
            renderSlots(data.slots || []);
        } catch (error) {
            slotsContainer.innerHTML = "";
            timeInput.value = "";
            setFeedback("No se pudo consultar la disponibilidad. Intenta nuevamente.", true);
        }
    };

    const renderCalendarDays = (payload) => {
        if (!calendarWidget) {
            return;
        }

        const monthLabel = calendarWidget.querySelector(".calendar-current-month");
        const daysContainer = calendarWidget.querySelector(".calendar-days");
        if (!monthLabel || !daysContainer) {
            return;
        }

        const [year, month] = currentMonth.split("-").map(Number);
        const baseDate = new Date(year, month - 1, 1);
        monthLabel.textContent = capitalize(
            new Intl.DateTimeFormat("es-DO", { month: "long", year: "numeric" }).format(baseDate)
        );

        daysContainer.innerHTML = "";

        const firstWeekday = payload?.first_weekday ?? getFirstWeekday(baseDate);
        for (let index = 0; index < firstWeekday; index += 1) {
            const spacer = document.createElement("span");
            spacer.className = "calendar-spacer";
            daysContainer.appendChild(spacer);
        }

        const dayItems = payload?.days ?? buildDisabledMonth(currentMonth);
        dayItems.forEach((dayItem) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "calendar-day";
            button.innerHTML = `
                <strong>${dayItem.day}</strong>
                <small>${dayItem.available ? `${dayItem.slots_count} horarios` : dayItem.disabled ? "No valido" : "Sin cupo"}</small>
            `;

            if (dayItem.disabled) {
                button.disabled = true;
                button.classList.add("is-disabled");
            } else if (!dayItem.available) {
                button.classList.add("is-unavailable");
            } else {
                button.classList.add("is-available");
            }

            if (dayItem.is_today) {
                button.classList.add("is-today");
            }

            if (selectedDate === dayItem.date) {
                button.classList.add("is-selected");
            }

            button.addEventListener("click", () => {
                if (button.disabled || !dayItem.available) {
                    return;
                }

                selectedDate = dayItem.date;
                dateInput.value = dayItem.date;
                timeInput.value = "";
                updateSelectedDateLabel();
                renderCalendarDays(payload);
                loadSlots();
            });

            daysContainer.appendChild(button);
        });
    };

    const loadCalendar = async () => {
        if (!calendarWidget) {
            updateSelectedDateLabel();
            return;
        }

        updateSelectedDateLabel();

        if (!serviceInput.value) {
            renderCalendarDays(null);
            setFeedback("Selecciona un servicio para activar el calendario.");
            return;
        }

        const params = new URLSearchParams({
            service_id: serviceInput.value,
            month: currentMonth,
        });

        if (barberInput && barberInput.value) {
            params.set("barber_id", barberInput.value);
        }

        try {
            const response = await fetch(`${calendarUrl}?${params.toString()}`);
            const data = await response.json();
            renderCalendarDays(data);
        } catch (error) {
            renderCalendarDays(null);
            setFeedback("No se pudo cargar el calendario. Intenta nuevamente.", true);
        }
    };

    if (calendarWidget) {
        const prevButton = calendarWidget.querySelector("[data-calendar-prev]");
        const nextButton = calendarWidget.querySelector("[data-calendar-next]");

        prevButton?.addEventListener("click", () => {
            currentMonth = shiftMonth(currentMonth, -1);
            loadCalendar();
        });

        nextButton?.addEventListener("click", () => {
            currentMonth = shiftMonth(currentMonth, 1);
            loadCalendar();
        });
    }

    [serviceInput, barberInput].forEach((field) => {
        field?.addEventListener("change", () => {
            timeInput.value = "";
            slotsContainer.innerHTML = "";
            loadCalendar();

            if (selectedDate) {
                loadSlots();
            }
        });
    });

    if (!calendarWidget) {
        dateInput.addEventListener("change", () => {
            selectedDate = dateInput.value;
            updateSelectedDateLabel();
            timeInput.value = "";
            loadSlots();
        });
    }

    phoneInput?.addEventListener("blur", () => {
        const digits = (phoneInput.value || "").replace(/\D/g, "");
        if (digits && ![10, 11].includes(digits.length)) {
            phoneInput.setCustomValidity("Ingresa un telefono valido de 10 u 11 digitos.");
        } else {
            phoneInput.setCustomValidity("");
        }
    });

    form.addEventListener("submit", (event) => {
        const phoneDigits = (phoneInput?.value || "").replace(/\D/g, "");

        if (!dateInput.value) {
            event.preventDefault();
            setFeedback("Debes elegir una fecha valida en el calendario.", true);
            return;
        }

        if (!timeInput.value) {
            event.preventDefault();
            setFeedback("Debes elegir una hora disponible antes de continuar.", true);
            return;
        }

        if (phoneInput && phoneDigits && ![10, 11].includes(phoneDigits.length)) {
            event.preventDefault();
            phoneInput.reportValidity();
        }
    });

    loadCalendar();
    if (selectedDate) {
        loadSlots();
    }
}

function shiftMonth(monthValue, delta) {
    const [year, month] = monthValue.split("-").map(Number);
    const nextDate = new Date(year, month - 1 + delta, 1);
    return toMonthValue(nextDate);
}

function toMonthValue(dateObject) {
    const year = dateObject.getFullYear();
    const month = `${dateObject.getMonth() + 1}`.padStart(2, "0");
    return `${year}-${month}`;
}

function getFirstWeekday(dateObject) {
    return (dateObject.getDay() + 6) % 7;
}

function buildDisabledMonth(monthValue) {
    const [year, month] = monthValue.split("-").map(Number);
    const totalDays = new Date(year, month, 0).getDate();
    const today = new Date();
    const days = [];

    for (let day = 1; day <= totalDays; day += 1) {
        const currentDate = new Date(year, month - 1, day, 12, 0, 0);
        const isoDate = currentDate.toISOString().slice(0, 10);
        const isPast = currentDate < new Date(today.getFullYear(), today.getMonth(), today.getDate(), 0, 0, 0);

        days.push({
            date: isoDate,
            day,
            available: false,
            disabled: true,
            slots_count: 0,
            is_today:
                currentDate.getFullYear() === today.getFullYear() &&
                currentDate.getMonth() === today.getMonth() &&
                currentDate.getDate() === today.getDate(),
        });
    }

    return days;
}

function capitalize(text) {
    if (!text) {
        return text;
    }
    return text.charAt(0).toUpperCase() + text.slice(1);
}

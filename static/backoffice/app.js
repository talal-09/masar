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

const workOrderForm = document.querySelector("[data-work-order-form]");
if (workOrderForm) {
    const optionsUrl = workOrderForm.dataset.optionsUrl;
    const branch = workOrderForm.querySelector("#id_branch");
    const customer = workOrderForm.querySelector("#id_customer");
    const vehicle = workOrderForm.querySelector("#id_vehicle");
    const technician = workOrderForm.querySelector("#id_assigned_technician");
    const receptionist = workOrderForm.querySelector("#id_created_by");

    const updateOptions = async (select, type, parentId, emptyLabel, noResultsLabel) => {
        select.disabled = true;
        select.replaceChildren(new Option(emptyLabel, ""));
        if (!parentId) return;
        try {
            const response = await fetch(`${optionsUrl}?type=${type}&parent=${parentId}`, {
                headers: {"X-Requested-With": "XMLHttpRequest"},
            });
            if (!response.ok) throw new Error("options request failed");
            const data = await response.json();
            select.replaceChildren(new Option(
                data.options.length ? emptyLabel : noResultsLabel,
                "",
            ));
            data.options.forEach((item) => {
                select.add(new Option(item.label, item.value));
            });
            select.disabled = data.options.length === 0;
        } catch (_error) {
            select.replaceChildren(new Option("تعذر تحميل الخيارات، حاول مجددًا", ""));
            select.disabled = true;
        }
    };

    customer?.addEventListener("change", () => {
        updateOptions(
            vehicle, "vehicles", customer.value,
            "اختر السيارة", "لا توجد سيارات مسجلة لهذا العميل",
        );
    });
    branch?.addEventListener("change", () => {
        updateOptions(
            technician, "technicians", branch.value,
            "اختر الفني", "لا يوجد فنيون فعالون في هذا الفرع",
        );
        updateOptions(
            receptionist, "receptionists", branch.value,
            "اختر موظف الاستقبال", "لا يوجد موظفو استقبال فعالون في هذا الفرع",
        );
    });
}

from django import forms

from .models import Customer, Vehicle


CAR_BRANDS = {
    "Toyota": ("Camry", "Corolla", "Yaris", "Land Cruiser", "RAV4", "Hilux"),
    "Lexus": ("ES", "IS", "LS", "NX", "RX", "LX"),
    "Nissan": ("Sunny", "Altima", "Maxima", "X-Trail", "Patrol", "Navara"),
    "Infiniti": ("Q30", "Q50", "Q60", "QX50", "QX60", "QX80"),
    "Honda": ("City", "Civic", "Accord", "HR-V", "CR-V", "Pilot"),
    "Acura": ("Integra", "TLX", "RLX", "RDX", "MDX", "NSX"),
    "Mazda": ("Mazda 3", "Mazda 6", "CX-3", "CX-5", "CX-60", "CX-9"),
    "Mitsubishi": ("Attrage", "Lancer", "ASX", "Eclipse Cross", "Outlander", "Pajero"),
    "Subaru": ("Impreza", "Legacy", "WRX", "XV", "Forester", "Outback"),
    "Suzuki": ("Dzire", "Swift", "Baleno", "Jimny", "Vitara", "Ertiga"),
    "Hyundai": ("Accent", "Elantra", "Sonata", "Creta", "Tucson", "Santa Fe"),
    "Kia": ("Pegas", "Cerato", "K5", "Seltos", "Sportage", "Sorento"),
    "Genesis": ("G70", "G80", "G90", "GV60", "GV70", "GV80"),
    "Ford": ("Taurus", "Mustang", "Territory", "Explorer", "Expedition", "F-150"),
    "Chevrolet": ("Spark", "Malibu", "Camaro", "Captiva", "Tahoe", "Silverado"),
    "GMC": ("Terrain", "Acadia", "Yukon", "Canyon", "Sierra", "Hummer EV"),
    "Cadillac": ("CT4", "CT5", "XT4", "XT5", "XT6", "Escalade"),
    "Jeep": ("Renegade", "Compass", "Cherokee", "Wrangler", "Gladiator", "Grand Cherokee"),
    "Dodge": ("Charger", "Challenger", "Durango", "Hornet", "Journey", "Ram"),
    "Chrysler": ("200", "300", "Pacifica", "Voyager", "Aspen", "Crossfire"),
    "Tesla": ("Model 3", "Model S", "Model X", "Model Y", "Cybertruck", "Roadster"),
    "Mercedes-Benz": ("A-Class", "C-Class", "E-Class", "S-Class", "GLC", "G-Class"),
    "BMW": ("1 Series", "3 Series", "5 Series", "7 Series", "X3", "X5"),
    "Audi": ("A3", "A4", "A6", "A8", "Q5", "Q8"),
    "Volkswagen": ("Polo", "Golf", "Passat", "T-Roc", "Tiguan", "Touareg"),
    "Porsche": ("718", "911", "Panamera", "Macan", "Cayenne", "Taycan"),
    "Volvo": ("S60", "S90", "XC40", "XC60", "XC90", "C40"),
    "Land Rover": ("Defender", "Discovery", "Discovery Sport", "Range Rover", "Range Rover Sport", "Evoque"),
    "Jaguar": ("XE", "XF", "XJ", "E-Pace", "F-Pace", "F-Type"),
    "Mini": ("Cooper", "Clubman", "Countryman", "Paceman", "Aceman", "Roadster"),
    "Renault": ("Symbol", "Megane", "Talisman", "Duster", "Koleos", "Captur"),
    "Peugeot": ("208", "301", "508", "2008", "3008", "5008"),
    "Citroen": ("C3", "C4", "C5", "C3 Aircross", "C5 Aircross", "Berlingo"),
    "Fiat": ("500", "Tipo", "Panda", "500X", "Doblo", "Ducato"),
    "Alfa Romeo": ("Giulia", "Giulietta", "Stelvio", "Tonale", "4C", "8C"),
    "Ferrari": ("Roma", "Portofino", "296 GTB", "SF90", "F8", "Purosangue"),
    "Lamborghini": ("Huracan", "Aventador", "Revuelto", "Urus", "Gallardo", "Murcielago"),
    "Maserati": ("Ghibli", "Quattroporte", "GranTurismo", "Grecale", "Levante", "MC20"),
    "Geely": ("Emgrand", "Preface", "Coolray", "Geometry C", "Monjaro", "Okavango"),
    "Changan": ("Alsvin", "Eado Plus", "UNI-V", "CS35 Plus", "CS75 Plus", "UNI-K"),
}

YEAR_CHOICES = [(year, str(year)) for year in range(2027, 1959, -1)]


FIELD_CLASS = (
    "mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 "
    "outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-500/10"
)


class CustomerProfileForm(forms.ModelForm):
    first_name = forms.CharField(label="الاسم", max_length=150)
    email = forms.EmailField(label="البريد الإلكتروني")

    class Meta:
        model = Customer
        fields = ("phone", "address")

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["first_name"].initial = user.first_name
        self.fields["email"].initial = user.email
        for field in self.fields.values():
            field.widget.attrs["class"] = FIELD_CLASS

    def save(self, commit=True):
        customer = super().save(commit=False)
        customer.full_name = self.cleaned_data["first_name"]
        customer.email = self.cleaned_data["email"]
        self.user.first_name = self.cleaned_data["first_name"]
        self.user.email = self.cleaned_data["email"]
        if commit:
            self.user.save(update_fields=["first_name", "email"])
            customer.save()
        return customer


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = (
            "plate_number",
            "chassis_number",
            "brand",
            "model",
            "year",
            "color",
            "mileage",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["brand"].widget = forms.Select(
            choices=[("", "اختر الشركة")] + [(brand, brand) for brand in CAR_BRANDS]
        )
        selected_brand = self.data.get("brand") or getattr(self.instance, "brand", "")
        selected_model = self.data.get("model") or getattr(self.instance, "model", "")
        model_choices = list(CAR_BRANDS.get(selected_brand, ()))
        if selected_model and selected_model not in model_choices:
            model_choices.append(selected_model)
        self.fields["model"].widget = forms.Select(
            choices=[("", "اختر الموديل")] + [(model, model) for model in model_choices]
        )
        self.fields["year"].widget = forms.Select(
            choices=[("", "اختر سنة الصنع")] + YEAR_CHOICES
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = FIELD_CLASS

    def clean(self):
        cleaned_data = super().clean()
        brand = cleaned_data.get("brand")
        model = cleaned_data.get("model")
        if brand and model and model not in CAR_BRANDS.get(brand, ()):
            self.add_error("model", "اختر موديلًا تابعًا للشركة المحددة.")
        return cleaned_data

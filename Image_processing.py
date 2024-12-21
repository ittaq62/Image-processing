
#      .--.
#      |o_o |   ittaq62 
#      |:_/ |   Logiciel - V1
#     //   \ \  
#    (|     | )
#   /'\_   _/`\
#   \___)=(___/

import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread, Event
from astroquery.simbad import Simbad
from astroquery.skyview import SkyView
from astropy import units as u
from astropy.io import fits
import numpy as np
import os
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
import subprocess
import platform

# Variable globale pour arrêter les résultats progressifs
arret_recherche = Event()

# Dictionnaire pour convertir les termes courants en codes Simbad
TYPE_OBJET_MAPPING = {
    "étoiles": "Star",
    "galaxies": "Galaxy",
    "nébuleuses": "Neb",
    "supernovae": "SNR",
    "amas": "Cluster*",
}

# Fonction pour remplir les pixels manquants dans les images
def remplir_pixels_manquants(data):
    """Remplit les zones avec des pixels manquants ou très faibles."""
    data = np.nan_to_num(data, nan=0.0)
    filled_data = data.copy()
    rows, cols = data.shape

    for i in range(1, rows - 1):
        for j in range(1, cols - 1):
            if filled_data[i, j] == 0:
                neighbors = [
                    data[i - 1, j], data[i + 1, j],
                    data[i, j - 1], data[i, j + 1],
                    data[i - 1, j - 1], data[i - 1, j + 1],
                    data[i + 1, j - 1], data[i + 1, j + 1]
                ]
                non_zero_neighbors = [v for v in neighbors if v > 0]
                if non_zero_neighbors:
                    filled_data[i, j] = np.mean(non_zero_neighbors)
    return filled_data

# Fonction pour obtenir les coordonnées avec Simbad
def obtenir_coordonnees(objet):
    try:
        result = Simbad.query_object(objet)
        if result is not None:
            ra = result["RA"][0]
            dec = result["DEC"][0]
            return f"RA: {ra}\nDEC: {dec}"
        else:
            return "Coordonnées introuvables pour cet objet."
    except Exception as e:
        return f"Erreur lors de la récupération des coordonnées : {e}"

# Fonction pour mettre à jour les coordonnées lors de la sélection d'un dossier téléchargé
def mettre_a_jour_coordonnees_dossier(event):
    dossier_selectionne = liste_telecharges.get()
    if dossier_selectionne:
        coordonnees = obtenir_coordonnees(dossier_selectionne)
        label_coordonnees.config(text=f"Coordonnées :\n{coordonnees}")

# Fonction pour télécharger des fichiers FITS depuis SkyView
def telecharger_fits():
    objet_selectionne = liste_deroulante.get()
    if not objet_selectionne:
        messagebox.showerror("Erreur", "Aucun objet sélectionné.")
        return

    def telecharger():
        barre_chargement.pack(fill="x", padx=10, pady=5)
        barre_chargement.start(10)

        chemin_dossier = os.path.join('./telechargements', objet_selectionne)
        os.makedirs(chemin_dossier, exist_ok=True)

        surveys = ("DSS2 Red", "DSS2 Blue", "DSS2 IR")
        radius = 0.1

        for survey in surveys:
            try:
                fits_files = SkyView.get_images(position=objet_selectionne, survey=survey, radius=radius * u.deg)
                file_path = os.path.join(chemin_dossier, f"{survey.replace(' ', '_')}.fit")
                if fits_files:
                    fits_files[0].writeto(file_path, overwrite=True)
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur pour {survey}: {e}")

        barre_chargement.stop()
        barre_chargement.pack_forget()
        charger_dossiers_telecharges()

    thread = Thread(target=telecharger, daemon=True)
    thread.start()

# Fonction pour gérer la recherche avec Simbad
def lancer_recherche():
    arret_recherche.set()
    barre_chargement.pack(fill="x", padx=10, pady=5)
    barre_chargement.start(10)
    liste_deroulante.set("")
    liste_deroulante['values'] = ()
    bouton_telecharger.pack_forget()

    def rechercher():
        arret_recherche.clear()
        try:
            Simbad.TIMEOUT = 30
            Simbad.ROW_LIMIT = 100
            type_objet = TYPE_OBJET_MAPPING.get(liste_telescope.get().strip().lower(), "Star")
            result = Simbad.query_criteria(otype=type_objet)

            if result is not None:
                objets = list(result["MAIN_ID"])
            else:
                objets = []

            if objets:
                liste_deroulante['values'] = tuple(objets)
                bouton_telecharger.pack(pady=5)
            else:
                print("Aucun résultat trouvé.")
        except Exception as e:
            print(f"Erreur lors de la recherche : {e}")
        finally:
            barre_chargement.stop()
            barre_chargement.pack_forget()

    thread = Thread(target=rechercher, daemon=True)
    thread.start()

# Fonction pour ouvrir le dossier cible
def ouvrir_dossier_cible():
    chemin_dossier = './telechargements/'
    if not os.path.exists(chemin_dossier):
        os.makedirs(chemin_dossier)
    if platform.system() == "Windows":
        subprocess.Popen(f'explorer "{os.path.abspath(chemin_dossier)}"')
    elif platform.system() == "Darwin":  # macOS
        subprocess.Popen(["open", chemin_dossier])
    else:  # Linux and others
        subprocess.Popen(["xdg-open", chemin_dossier])

# Fonction pour afficher les images d'un dossier sélectionné
def afficher_images():
    dossier_selectionne = liste_telecharges.get()
    if not dossier_selectionne or dossier_selectionne == "Aucun téléchargement":
        messagebox.showerror("Erreur", "Veuillez sélectionner un dossier valide.")
        return

    chemin_dossier = os.path.join('./telechargements/', dossier_selectionne)
    file_paths = [
        os.path.join(chemin_dossier, f)
        for f in os.listdir(chemin_dossier)
        if f.endswith(".fit") or f.endswith(".fits")
    ]

    if len(file_paths) != 3:
        messagebox.showerror("Erreur", f"Le dossier doit contenir exactement 3 fichiers FITS. Fichiers trouvés : {len(file_paths)}")
        return

    # Obtenir les coordonnées Simbad
    coordonnees = obtenir_coordonnees(dossier_selectionne)
    label_coordonnees.config(text=f"Coordonnées :\n{coordonnees}")

    # Charger et normaliser les images FITS
    channels = []
    for file_path in file_paths:
        try:
            data = fits.getdata(file_path)
            data = np.clip(data, 0, np.percentile(data, 99))
            data = (data - data.min()) / (data.max() - data.min())
            channels.append(data)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur avec {file_path}: {e}")
            return

    if len(channels) != 3:
        messagebox.showerror("Erreur", "Impossible de charger les trois canaux.")
        return

    def update_image(val):
        r_weight = slider_r.val
        g_weight = slider_g.val
        b_weight = slider_b.val
        vmax = slider_vmax.val

        rgb_image = np.dstack((channels[0] * r_weight, channels[1] * g_weight, channels[2] * b_weight))
        rgb_image = np.clip(rgb_image, 0, vmax)

        image.set_data(rgb_image)
        fig.canvas.draw_idle()

    fig, ax = plt.subplots(figsize=(8, 8))
    plt.subplots_adjust(bottom=0.35)

    rgb_image = np.dstack((channels[0], channels[1], channels[2]))
    rgb_image = np.clip(rgb_image, 0, 1)
    image = ax.imshow(rgb_image, origin='lower')
    ax.axis('off')

    ax_r = plt.axes([0.25, 0.2, 0.65, 0.03])
    ax_g = plt.axes([0.25, 0.15, 0.65, 0.03])
    ax_b = plt.axes([0.25, 0.1, 0.65, 0.03])
    ax_vmax = plt.axes([0.25, 0.05, 0.65, 0.03])

    slider_r = Slider(ax_r, 'Rouge', 0.0, 2.0, valinit=1.0)
    slider_g = Slider(ax_g, 'Vert', 0.0, 2.0, valinit=1.0)
    slider_b = Slider(ax_b, 'Bleu', 0.0, 2.0, valinit=1.0)
    slider_vmax = Slider(ax_vmax, 'Vmax', 0.1, 1.0, valinit=1.0)

    slider_r.on_changed(update_image)
    slider_g.on_changed(update_image)
    slider_b.on_changed(update_image)
    slider_vmax.on_changed(update_image)

    plt.show()

# Fonction pour charger les dossiers téléchargés
def charger_dossiers_telecharges():
    chemin_dossier = './telechargements/'
    if not os.path.exists(chemin_dossier):
        os.makedirs(chemin_dossier)
    dossiers = [d for d in os.listdir(chemin_dossier) if os.path.isdir(os.path.join(chemin_dossier, d))]
    if dossiers:
        liste_telecharges['values'] = dossiers
        liste_telecharges.set("Sélectionnez un dossier")
    else:
        liste_telecharges['values'] = ()
        liste_telecharges.set("Aucun téléchargement")

# Création de la fenêtre principale
fenetre = tk.Tk()
fenetre.title("Image processing")
fenetre.geometry("750x550")
fenetre.configure(bg="#f8f9fa")

style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", font=("Arial", 10), padding=5)
style.configure("TCombobox", font=("Arial", 10))

label_titre = tk.Label(fenetre, text="Logiciel de recherche et téléchargement d'images astronomique", bg="#f8f9fa", font=("Arial", 14, "bold"))
label_titre.pack(pady=20)

cadre = tk.Frame(fenetre, bg="#f8f9fa")
cadre.pack(expand=True, pady=20)

# Zone Téléchargements
cadre_gauche = tk.Frame(cadre, bg="#e7f4ff", bd=2, relief="groove", width=300, height=300)
cadre_gauche.grid(row=0, column=0, padx=20, pady=10)
cadre_gauche.pack_propagate(False)

label_gauche = tk.Label(cadre_gauche, text="Téléchargements :", bg="#e7f4ff", font=("Arial", 12))
label_gauche.pack(padx=10, pady=10)

liste_telescope = ttk.Combobox(cadre_gauche, values=list(TYPE_OBJET_MAPPING.keys()), state="readonly", width=35)
liste_telescope.set("étoiles")
liste_telescope.pack(pady=10)

liste_deroulante = ttk.Combobox(cadre_gauche, width=35)
liste_deroulante.pack(pady=10)

barre_chargement = ttk.Progressbar(cadre_gauche, mode="indeterminate")
barre_chargement.pack_forget()

bouton_recherche = ttk.Button(cadre_gauche, text="Lancer la recherche", command=lancer_recherche)
bouton_recherche.pack(pady=10)

bouton_telecharger = ttk.Button(cadre_gauche, text="Télécharger", command=telecharger_fits)
bouton_telecharger.pack_forget()

# Zone Téléchargés
cadre_droit = tk.Frame(cadre, bg="#e7ffe7", bd=2, relief="groove", width=300, height=300)
cadre_droit.grid(row=0, column=1, padx=20, pady=10)
cadre_droit.pack_propagate(False)

label_droit = tk.Label(cadre_droit, text="Téléchargés :", bg="#e7ffe7", font=("Arial", 12))
label_droit.pack(padx=10, pady=10)

liste_telecharges = ttk.Combobox(cadre_droit, width=35)
liste_telecharges.pack(pady=10)
liste_telecharges.bind("<<ComboboxSelected>>", mettre_a_jour_coordonnees_dossier)

label_coordonnees = tk.Label(cadre_droit, text="Coordonnées : Non défini", bg="#e7ffe7", font=("Arial", 10), wraplength=250, justify="left")
label_coordonnees.pack(pady=5)

bouton_afficher = ttk.Button(cadre_droit, text="Afficher", command=afficher_images)
bouton_afficher.pack(pady=10)

bouton_ajouter = ttk.Button(cadre_droit, text="Ajouter votre propre observation 📁", command=ouvrir_dossier_cible)
bouton_ajouter.pack(pady=10)

charger_dossiers_telecharges()

fenetre.mainloop()

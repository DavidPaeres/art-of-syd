import cv2
import numpy as np
import os

points = []

def click_event(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
        points.append((x, y))
        cv2.circle(img, (x, y), 5, (0, 255, 0), -1)
        cv2.imshow("Selecciona 4 esquinas", img)

# Nombres de directorios para imagenes originales y recortadas
input_folder = "imagenes_originales"
output_folder = "imagenes_recortadas"
os.makedirs(output_folder, exist_ok=True)

image_files = [f for f in os.listdir(input_folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

for filename in image_files:
    print(f"\n📷 Procesando: {filename}")
    points = []
    input_image_path = os.path.join(input_folder, filename)

    # Leer imagen
    img = cv2.imread(input_image_path)
    if img is None:
        print(f"❌ No se pudo cargar la imagen: {input_image_path}")
        continue

    clone = img.copy()

    # Mostrar imagen y capturar clics
    cv2.namedWindow("Selecciona 4 esquinas", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("Selecciona 4 esquinas", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.imshow("Selecciona 4 esquinas", img)
    cv2.setMouseCallback("Selecciona 4 esquinas", click_event)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    if len(points) != 4:
        print("❌ Debes seleccionar exactamente 4 puntos en el orden: arriba-izq, arriba-der, abajo-der, abajo-izq.")
        continue

    # Procesar los 4 puntos
    pts_src = np.array(points, dtype="float32")

    # Calcular el tamaño de la imagen corregida
    width_top = np.linalg.norm(pts_src[0] - pts_src[1])
    width_bottom = np.linalg.norm(pts_src[3] - pts_src[2])
    width = int(max(width_top, width_bottom))

    height_left = np.linalg.norm(pts_src[0] - pts_src[3])
    height_right = np.linalg.norm(pts_src[1] - pts_src[2])
    height = int(max(height_left, height_right))

    # Definir los puntos destino (rectángulo)
    pts_dst = np.array([
        [0, 0],
        [width - 1, 0],
        [width - 1, height - 1],
        [0, height - 1]
    ], dtype="float32")

    # Obtener matriz de transformación y aplicar
    M = cv2.getPerspectiveTransform(pts_src, pts_dst)
    warped = cv2.warpPerspective(clone, M, (width, height))

    # Generando prefijo del nombre de la imagen
    name, ext = os.path.splitext(filename)
    output_filename = f"{width}x{height}_{name}{ext}"
    output_path = os.path.join(output_folder, output_filename)

    # Guardar recorte
    cv2.imwrite(output_path, warped)
    print(f"✅ Imagen recortada guardada como: {output_path}")

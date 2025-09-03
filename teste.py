from PIL import Image

# só para confirmar que o Pillow está instalado
img = Image.new("RGB", (100, 100), color="red")
img.show()
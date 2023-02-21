import subprocess


#kubectl get pods --all-namespaces -o jsonpath="{..image}" | tr -s '[[:space:]]' '\n' | sort | uniq

def scan_all_images():

    images = subprocess.check_output("kubectl get pods --all-namespaces -o jsonpath='{.items[*].spec.containers[*].image}'", shell=True).decode('utf-8').split()


    for image in images:
        command = "kube-hunter image " + image
        output = subprocess.check_output(command, shell=True).decode('utf-8')
        print(output)

if __name__ == "__main__":
    scan_all_images()

"""  
#oppure

import os
import subprocess

# Esegui il comando "kubectl get pods" e analizza l'output per ottenere una lista di tutte le immagini presenti nel cluster
pods_output = subprocess.check_output(["kubectl", "get", "pods", "--all-namespaces", "-o", "jsonpath='{.items[*].spec.containers[*].image}'"])
images = set(pods_output.decode("utf-8").replace("'", "").split())

# Esegui la scansione di sicurezza per ogni immagine trovata
for image in images:
    print(f"Scanning {image}...")
    os.system(f"kube-hunter image {image}")
"""

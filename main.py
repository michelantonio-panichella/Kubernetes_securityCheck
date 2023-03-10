import os
import kubernetes
from google.auth.transport import requests
from kubernetes import client, config
from kubernetes.client.rest import ApiException


def namespaceTest(namespace):
    # Carica la confi gurazione di Kubernetes
    config.load_kube_config()


    # Istanzia le API del client
    core_v1 = client.CoreV1Api()
    rbac_v1 = client.RbacAuthorizationV1Api()
    v1_ext = client.ExtensionsV1beta1Api()
    namespace_name = "default"

    # Controlla se il namespace esiste
    try:
        api_response = core_v1.read_namespace(name=namespace_name)
        print(f'Success: Namespace {namespace_name} esiste.')
    except ApiException as e:
        if e.status == 404:
            print(f"Il namespace {namespace_name} non esiste.")
        else:
            print("Errore durante la ricerca del namespace:", e)

    # Effettua una chiamata all'API Kubernetes per ottenere le informazioni sul namespace se l'utente possiede i privilegi vengono restituite le informazioni altrimenti viene stampato errore durante la chiamata all'API Kubernetes
    try:
        api_response = core_v1.read_namespace(name=namespace_name)
        print(f"L'utente ha i privilegi per accedere al namespace {namespace_name}.")
    except ApiException as e:
        if e.status == 403:
            print(f"L'utente non ha i privilegi per accedere al namespace {namespace_name}.")
        else:
            print("Errore durante la chiamata all'API Kubernetes: %s\n" % e)



    # Verifica della configurazione delle regole di sicurezza del network
    try:
        v1_ext = client.ExtensionsV1beta1Api()
        network_policies = v1_ext.list_namespaced_network_policy(namespace, pretty=True)
        if network_policies.items:
            print("Regole di sicurezza del network configurate correttamente")
        else:
            print("Nessuna regola di sicurezza del network configurata per il namespace")
    except kubernetes.client.rest.ApiException as e:
        print("Errore nella verifica della configurazione delle regole di sicurezza del network", e)


    # Verifica della configurazione della crittografia delle comunicazioni
    try:
        secrets = core_v1.list_namespaced_secret(namespace, pretty=True)
        has_tls_cert = False
        for secret in secrets.items:
            if "tls.crt" in secret.data and "tls.key" in secret.data:
                has_tls_cert = True
                break
        if has_tls_cert:
            print("Crittografia delle comunicazioni configurata correttamente")
        else:
            print("Nessuna crittografia delle comunicazioni configurata per il namespace")

        print("Verifica della sicurezza del namespace completata")
    except kubernetes.client.rest.ApiException as e:
        print("Errore nella verifica della configurazione della crittografia delle comunicazioni", e)


    # Autenticazione con le credenziali appropriate
    kubernetes.config.load_kube_config()
    v1 = client.CoreV1Api()

    # Elenco di tutti i namespace
    namespaces = v1.list_namespace().items

    # Elenco degli utenti autorizzati
    authorized_users = ['user1', 'user2', 'user3']

    for namespace in namespaces:
        # Verifica che l'utente abbia accesso solo se autorizzato
        if namespace.metadata.annotations['openshift.io/requester'] not in authorized_users:
            print("Accesso negato per l'utente: ", namespace.metadata.annotations['openshift.io/requester'])
        else:
            print("Accesso autorizzato per l'utente: ", namespace.metadata.annotations['openshift.io/requester'])





    # Verifica che tutti i namespace abbiano una configurazione di sicurezza appropriata
    for namespace in namespaces:
        try:
            # Verifica che la configurazione di sicurezza sia presente
            if 'openshift.io/sa.scc.uid-range' not in namespace.metadata.annotations:
                print("Configurazione di sicurezza non presente per il namespace: ", namespace.metadata.name)
            else:
                # Verifica che la configurazione di sicurezza sia corretta
                if namespace.metadata.annotations['openshift.io/sa.scc.uid-range'] != '1-4294967295':
                    print("Configurazione di sicurezza non corretta per il namespace: ", namespace.metadata.name)
                else:
                    print("Configurazione di sicurezza corretta per il namespace: ", namespace.metadata.name)
        except ApiException as e:
            print("Errore durante la verifica della configurazione di sicurezza per il namespace: ", namespace.metadata.name)



    # Verifica dei privilegi per ogni namespace
    for namespace in namespaces:
        # Elenco di tutti i Pod nel namespace
        pods = v1.list_namespaced_pod(namespace.metadata.name).items
        for pod in pods:
            # Verifica che ogni contenitore nel Pod abbia solo i privilegi di sistema necessari
            for container in pod.spec.containers:
                if 'privileged' in container.security_context:
                    if container.security_context['privileged'] == True:
                        print("Il contenitore ha privilegi elevati: ", container.name, "nel Pod: ", pod.metadata.name)
                    else:
                        print("Il contenitore non ha privilegi elevati: ", container.name, "nel Pod: ", pod.metadata.name)
                else:
                    print("Il contenitore non ha privilegi elevati: ", container.name, "nel Pod: ", pod.metadata.name)



    # Creare un oggetto di tipo Configuration
    configuration = client.Configuration()

    # Creare un client API per la gestione degli utenti
    api_instance = client.UserAccountsApi(client.ApiClient(configuration))

    # Verificare l'elenco degli utenti autenticati
    try:
        users = api_instance.list_user()
        for user in users.items:
            print("Username:", user.metadata.name)
    except ApiException as e:
        print("Errore durante la richiesta API: %s\n" % e)



def kube_generaltest():


    # Load the kubernetes configuration
    config.load_kube_config()

    # Create a CoreV1Api client instance
    v1 = client.CoreV1Api()

    # Retrieve a list of all pods in the cluster
    pods = v1.list_pod_for_all_namespaces(watch=False)

    # Iterate through each pod
    for pod in pods.items:
        # Check if the pod is running with privileged mode
        if pod.spec.host_pid:
            print("Pod %s is running with privileged mode" % pod.metadata.name)

        # Check if the pod has memory and CPU limits set
        if not pod.spec.containers[0].resources.limits:
            print("Pod %s does not have memory and CPU limits set" % pod.metadata.name)
        else:
            print("Pod %s has memory and CPU limits set" % pod.metadata.name)


    # ---------------- Testa se Kubernetes ?? aggiornato
    # Get the current version of the cluster
    version_info = v1.get_code().to_dict()
    cluster_version = version_info["gitVersion"].split("+")[0]

    # Get the latest version of Kubernetes from the upstream repository
    response = requests.get("https://dl.k8s.io/release/stable.txt")
    if response.status_code == 200:
        latest_version = response.text.strip()
    else:
        print("Unable to retrieve latest Kubernetes version")

    # Compare the versions to determine if the cluster is up-to-date
    if cluster_version == latest_version:
        print("Kubernetes cluster is up-to-date")
    else:
        print("Kubernetes cluster is out-of-date. Current version: %s, Latest version: %s" % (
        cluster_version, latest_version))



print("Benvenuto in Check8s, cosa vuoi verificare ?")
print('Qui puoi verificare la sicurezza di', end='\n 1 ')
print('Namespaces', end='\n 2 ')
print('Container/Image', end='\n 3 ')
print('Endpoint esposti \n scegli! 1, 2 o 3 ?')
input_utente = int(input('1, 2, 3?'))
try:
    if(input_utente == 1):
        print('Benissimo, hai scelto di verificare un namespace')
    elif(input_utente == 2):
        print('Benissimo, hai scelto di verificare un \'immagine')
    else:
        if(input_utente == 3):
            print('Benissimo, hai scelto di verificare un endpoint')
except:
    print('mi dispiace l'i)



"""
Per utilizzare questo codice in Kubernetes, ?? necessario creare una configurazione di Pod 
che esegua questo codice come un contenitore. Ecco un esempio di configurazione di Pod in YAML:

yaml
Copy code
apiVersion: v1
kind: Pod
metadata:
  name: security-check
spec:
  containers:
  - name: security-check
    image: python:3.9
    command: ["python", "/app/security_check.py"]
    volumeMounts:
    - name: security-check-volume
      mountPath: /app
  volumes:
  - name: security-check-volume
    configMap:
      name: security-check-configmap
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: security-check-configmap
data:
  security_check.py: |
    # paste the Python code here
    
    
In questa configurazione, viene creato un Pod che esegue un contenitore basato sull'immagine Python python:3.9. 
Il contenitore esegue il codice Python utilizzando il comando ["python", "/app/security_check.py"]. 
Il codice viene montato nel contenitore utilizzando un volume di ConfigMap.

Per applicare questa configurazione in un cluster di Kubernetes, 
?? possibile utilizzare il comando kubectl apply -f security-check.yaml. 
Una volta che il Pod ?? in esecuzione, ?? possibile utilizzare il comando kubectl logs security-check per visualizzare i risultati del controllo di sicurezza.

Nota: ?? necessario modificare il codice per adattarlo alle proprie esigenze, 
come ad esempio specificare il nome del namespace e il nome utente da utilizzare per il controllo di sicurezza.

"""



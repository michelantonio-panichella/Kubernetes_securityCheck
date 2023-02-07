import os
import kubernetes
from kubernetes import client, config
from kubernetes.client.rest import ApiException


print("Benvenuti!, verifichiamo la sicurezza!")
print("Mi dici il nome del tuo namespace ?")

print("Grazie, verifico la tue configurazioni!")


# Nome del namespace da controllar
namespace = 'test-namespace'

def namespaceTest(namespace):
    # Carica la configurazione di Kubernetes
    config.load_kube_config()

    # Istanzia le API del client
    core_v1 = client.CoreV1Api()
    rbac_v1 = client.RbacAuthorizationV1Api()
    v1_ext = client.ExtensionsV1beta1Api()

    # Controlla se il namespace esiste
    try:
        api_response = core_v1.read_namespace(name=namespace)
        print(f'Success: Namespace {namespace} esiste.')
    except ApiException as e:
        print(f'Error: {e}')


    # Controlla se l'utente ha i privilegi per accedere al namespace
    try:
        # Recupera il nome del servizio account dell'utente corrente
        service_account_name = os.environ['SERVICE_ACCOUNT_NAME']
        # Recupera il nome del ruolo che assegna i privilegi di lettura al namespace
        role_name = 'namespace-reader'
        # Recupera la configurazione del ruolo
        role_config = rbac_v1.read_namespaced_role(name=role_name, namespace=namespace)
        # Controlla se il servizio account è presente tra i soggetti del ruolovisu
        for subject in role_config.subjects:
            if subject.name == service_account_name:
                print(
                    f'Success: Il servizio account {service_account_name} ha i privilegi di lettura sul namespace {namespace}.')
                break
        else:
            print(
                f'Error: Il servizio account {service_account_name} non ha i privilegi di lettura sul namespace {namespace}.')
    except ApiException as e:
        print(f'Error: {e}')


    # Verifica della configurazione delle regole di sicurezza del network
    try:
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


print("Benvenuti!, verifichiamo la sicurezza!")
print("Mi dici il nome del tuo namespace ?")

print("Grazie, verifico la tue configurazioni!")

namespaceTest(namespace)
import os
import kubernetes
from google.auth.transport import requests
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.watch import watch
import time


def verificaE():
# Carica la configurazione di Kubernetes
    config.load_kube_config()

# Istanzia le API del client
    core_v1 = client.CoreV1Api()
    rbac_v1 = client.RbacAuthorizationV1Api()
    v1_ext = client.ExtensionsV1beta1Api()
    namespace_name = "default"

# Elenco di tutti i namespace
    namespaces = core_v1.list_namespace().items


#------------------ Controlla se il namespace esiste
    try:
        api_response = core_v1.read_namespace(name=namespace_name)
        print(f'Success: Namespace {namespace_name} esiste.')
    except ApiException as e:
        if e.status == 404:
            print(f"Il namespace {namespace_name} non esiste.")
        else:
            print("Errore durante la ricerca del namespace:", e)


# ---------------- Testa se Kubernetes è aggiornato
    # Get the current version of the cluster
    version_info = core_v1.get_code().to_dict()
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


#---------------- Effettua una chiamata all'API Kubernetes per ottenere le informazioni sul namespace se l'utente possiede i privilegi vengono restituite le informazioni altrimenti viene stampato errore durante la chiamata all'API Kubernetes
    try:
        api_response = core_v1.read_namespace(name=namespace_name)
        print(f"L'utente ha i privilegi per accedere al namespace {namespace_name}.")
    except ApiException as e:
        if e.status == 403:
            print(f"L'utente non ha i privilegi per accedere al namespace {namespace_name}.")
        else:
            print("Errore durante la chiamata all'API Kubernetes: %s\n" % e)


#----------------- Verifica dei privilegi per ogni namespace

#--L'oggetto "security context" può contenere diversi campi, tra cui ad esempio:
#--privileged: se impostato su True, il container viene eseguito con privilegi elevati, che possono compromettere la sicurezza del cluster.
#--runAsUser e runAsGroup: specificano l'identità dell'utente e del gruppo utilizzati per eseguire il processo del container.
#--capabilities: specifica le capacità del kernel Linux che sono disponibili per il container. Le capacità possono essere limitate per migliorare la sicurezza del cluster.
#--seLinuxOptions e appArmorProfile: specificano le politiche di sicurezza applicate al container utilizzando SELinux e AppArmor, rispettiàvamente.
    for namespace in namespaces:
        # Elenco di tutti i Pod nel namespace
        pods = core_v1.list_namespaced_pod(namespace.metadata.name).items
        for pod in pods:
            # Verifica che ogni container nel Pod abbia solo i privilegi di sistema necessari
            for container in pod.spec.containers:
                if 'privileged' in container.security_context:
                    if container.security_context['privileged'] == True:
                        print("Attenzione il container ha privilegi elevati: ", container.name, "nel Pod: ", pod.metadata.name)
                    else:
                        print("Il container non ha privilegi elevati: ", container.name, "nel Pod: ", pod.metadata.name)
                else:
                    print("Il container non ha privilegi elevati: ", container.name, "nel Pod: ", pod.metadata.name)


#----------------- Controllo RBAC

    # Imposta la configurazione del client Kubernetes
    config.load_kube_config()

    # Definisce il nome del namespace e il nome della risorsa da verificare
    namespace_name = "mio-namespace"
    resource_name = "mio-pod"

    # Ottiene il nome dell'utente corrente dal contesto Kubernetes
    user_name = client.configuration.Configuration().get_default_copy().username

    # Verifica se l'utente ha il permesso di visualizzare la risorsa nel namespace
    v1 = client.RbacAuthorizationV1Api()
    role_bindings = v1.list_namespaced_role_binding(namespace_name).items

    for binding in role_bindings:
        for subject in binding.subjects:
            if subject.kind == "User" and subject.name == user_name:
                role_name = binding.role_ref.name
                role = v1.read_namespaced_role(role_name, namespace_name)
                for rule in role.rules:
                    if rule.api_groups == [""] or "core" in rule.api_groups:
                        if rule.resources == ["*"] or resource_name in rule.resources:
                            if "get" in rule.verbs:
                                print("L'utente", user_name, "ha il permesso di visualizzare la risorsa", resource_name,
                                    "nel namespace", namespace_name)
                                exit(0)

    # Se l'utente non ha i permessi per visualizzare la risorsa, stampa un messaggio di errore
    print("L'utente", user_name, "non ha il permesso di visualizzare la risorsa", resource_name, "nel namespace",
        namespace_name)
    exit(1)


#-------------- Verifica se i ruoli di un namespace vengono correttamente utilizzati
    # Definisce il nome del namespace e il nome del ruolo da verificare
    namespace_name = "mio-namespace"
    role_name = "mio-ruolo"

    # Crea un'istanza del client RBAC per accedere ai ruoli e ai binding nel namespace specificato
    rbac_client = client.RbacAuthorizationV1Api()

    # Crea un dizionario vuoto per tenere traccia degli utenti e dei servizi a cui è stato assegnato il ruolo
    assigned_to = {}

    # Definisce la funzione per elaborare i binding dei ruoli
    def process_role_binding(rb):
        for subject in rb.subjects:
            if subject.kind == "ServiceAccount":
                assigned_to[subject.name] = "ServiceAccount"
            elif subject.kind == "User":
                assigned_to[subject.name] = "User"

    # Inizia a monitorare i binding dei ruoli nel namespace specificato
    w = watch.Watch()
    for event in w.stream(rbac_client.list_namespaced_role_binding, namespace=namespace_name):
        if event['type'] == 'ADDED' or event['type'] == 'MODIFIED':
            rb = event['object']
            if rb.role_ref.name == role_name:
                process_role_binding(rb)

    # Termina la connessione di watch dopo 30 secondi
    time.sleep(30)
    w.stop()

    # Verifica se il ruolo è stato assegnato correttamente
    for name, subject_type in assigned_to.items():
        print("Il ruolo", role_name, "è stato assegnato a", subject_type, name)

    if not assigned_to:
        print("Il ruolo", role_name, "non è stato assegnato a nessun utente o servizio nel namespace", namespace_name)


#----------------Verifica che tutti i namespace abbiano una configurazione di sicurezza appropriata
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


#---------------- Verificare le autorizzazioni di accesso per un namespace:

    # Definisce il nome del namespace che si desidera controllare
    namespace_name = "nome-del-namespace"

    # Crea un'istanza del client per l'API di autorizzazione di Kubernetes
    auth_api = client.AuthorizationV1Api()

    # Recupera i ruoli associati al namespace
    role_list = auth_api.list_namespaced_role(namespace_name)

    # Recupera i cluster role associati al namespace
    cluster_role_list = auth_api.list_cluster_role()

    # Recupera i binding di ruoli associati al namespace
    role_binding_list = auth_api.list_namespaced_role_binding(namespace_name)

    # Recupera i binding di cluster role associati al namespace
    cluster_role_binding_list = auth_api.list_cluster_role_binding()

    # Verifica che solo gli utenti autorizzati abbiano accesso al namespace
    authorized_users = set()

    # Verifica i ruoli e i binding di ruoli associati al namespace
    for role in role_list.items:
        for rule in role.rules:
            for api_group in rule.api_groups:
                if api_group == "" or api_group == "rbac.authorization.k8s.io":
                    for resource in rule.resources:
                        authorized_users.update(auth_api.list_namespaced_role_binding(
                            namespace_name, label_selector=f"role-ref-name={role.metadata.name}").items)

    # Verifica i cluster role e i binding di cluster role associati al namespace
    for cluster_role in cluster_role_list.items:
        for rule in cluster_role.rules:
            for api_group in rule.api_groups:
                if api_group == "" or api_group == "rbac.authorization.k8s.io":
                    for resource in rule.resources:
                        authorized_users.update(auth_api.list_cluster_role_binding(
                            label_selector=f"role-ref-name={cluster_role.metadata.name}").items)

    # Verifica che solo gli utenti autorizzati abbiano accesso al namespace
    for binding in role_binding_list.items + cluster_role_binding_list.items:
        if not any(subject in authorized_users for subject in binding.subjects):
            print(f"ERRORE: Il binding di ruolo {binding.metadata.name} consente l'accesso a utenti non autorizzati.")


#---------------- verificare che i binding di ruoli non concedano autorizzazioni per l'esecuzione di comandi pericolosi
                # o per l'accesso a risorse sensibili, ad esempio credenziali di accesso o informazioni di identificazione personale

#In questo script, si utilizza il client Kubernetes API per controllare che i binding di ruoli non concedano autorizzazioni
# per l'esecuzione di comandi pericolosi o per l'accesso a risorse sensibili. Per fare ciò, si verificano le regole di ogni
# ruolo associato al binding di ruolo e si cercano regole che concedano l'accesso a risorse come i segreti o consentano l'esecuzione
# di comandi pericolosi come l'esecuzione di comandi all'interno dei pod. Se viene trovata una regola corrispondente, viene stampato
# un messaggio di avviso o errore, a seconda del caso.

    # Definisce il nome del namespace che si desidera controllare
    namespace_name = "nome-del-namespace"

    # Verifica che i binding di ruoli non concedano autorizzazioni per l'esecuzione di comandi pericolosi
    for binding in role_binding_list.items:
        for subject in binding.subjects:
            if subject.kind == "User" or subject.kind == "Group":
                for role in binding.role_ref:
                    for rule in [r for r in role_list.items if r.metadata.name == role.name][0].rules:
                        for api_group in rule.api_groups:
                            if api_group == "" or api_group == "rbac.authorization.k8s.io":
                                for resource in rule.resources:
                                    for verb in rule.verbs:
                                        if verb in ["create", "delete", "deletecollection", "update", "patch"] and resource in ["pods/exec", "pods/attach", "pods/portforward"]:
                                            print(f"ERRORE: Il binding di ruolo {binding.metadata.name} consente l'esecuzione di comandi pericolosi ({verb} {resource}) per l'utente o il gruppo {subject.name}.")

    # Verifica che i binding di ruoli non concedano autorizzazioni per l'accesso a risorse sensibili
    for binding in role_binding_list.items:
        for subject in binding.subjects:
            if subject.kind == "User" or subject.kind == "Group":
                for role in binding.role_ref:
                    for rule in [r for r in role_list.items if r.metadata.name == role.name][0].rules:
                        for api_group in rule.api_groups:
                            if api_group == "" or api_group == "rbac.authorization.k8s.io":
                                for resource in rule.resources:
                                    if resource in ["secrets", "configmaps"]:
                                        print(f"AVVISO: Il binding di ruolo {binding.metadata.name} concede l'accesso alla risorsa sensibile {resource} all'utente o al gruppo {subject.name}.")


#-------------- Verifica limiti risorse impostati
# Recupera i pod associati al namespace
    pod_list = core_v1.list_namespaced_pod(namespace_name)
    for pod in pod_list.items:
        for container in pod.spec.containers:
            if container.resources.limits is None:
                print(f"AVVISO: Il contenitore {container.name} nel pod {pod.metadata.name} non ha limiti di risorse impostati.")


#----------------- Verifica della configurazione della crittografia delle comunicazioni
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



##### ricordati di inserire controllo se da un altro nampespace posso accedere ad un altro senza problemi


# Verifica che tutti i comandi utili siano installati
#####################################################

if ! command -v lsblk > /dev/null; then
    echo " --> ATTENZIONE! lsblk non e' installato. Per favore, installalo con 'sudo apt-get install lsblk' e riprova."
    exit 2
fi	

if ! command -v dd > /dev/null; then
    echo " --> ATTENZIONE! dd non e' installato. Per favore, installalo con 'sudo apt-get install dd' e riprova."
    exit 2
fi	

if ! command -v git > /dev/null; then
    echo " --> ATTENZIONE! git non e' installato. Per favore, installalo con 'sudo apt-get install git' e riprova."
    exit 2
fi	

if ! command -v sshfs > /dev/null; then
    echo " --> ATTENZIONE! sshfs non e' installato. Per favore, installalo con 'sudo apt-get install sshfs' e riprova."
    exit 2
fi	

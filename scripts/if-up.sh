#!/bin/sh

FLAGFILE=/var/run/work-was-already-done

case "$IFACE" in
    lo)
        # The loopback interface does not count.
        # only run when some other interface comes up
        exit 0
        ;;
    *)
        ;;
esac

if [ -e $FLAGFILE ]; then
    exit 0
else
    touch $FLAGFILE
fi

/usr/sbin/service home-agent restart

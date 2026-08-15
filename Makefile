APP_NAME ?= unifi-protect-viewer
ROKU_DEV_TARGET ?=
ROKU_DEV_PASSWORD ?=

.PHONY: package package-ha install clean

package:
	rm -f $(APP_NAME).zip
	zip -r $(APP_NAME).zip manifest source components images -x '*.DS_Store'

package-ha:
	rm -f unifi_roku_bridge_home_assistant.zip
	zip -r unifi_roku_bridge_home_assistant.zip custom_components/unifi_roku_bridge -x '*.DS_Store' -x '*__pycache__*'

install: package
	curl --digest -u rokudev:$(ROKU_DEV_PASSWORD) \
		-F "mysubmit=Install" \
		-F "archive=@$(APP_NAME).zip" \
		http://$(ROKU_DEV_TARGET)/plugin_install

clean:
	rm -f $(APP_NAME).zip unifi_roku_bridge_home_assistant.zip

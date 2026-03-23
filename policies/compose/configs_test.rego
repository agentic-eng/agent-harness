package compose.configs_test

import data.compose.configs
import rego.v1

test_inline_content_denied if {
	count(configs.deny) > 0 with input as {"configs": {"myconfig": {"content": "some data"}}}
}

test_file_config_passes if {
	count(configs.deny) == 0 with input as {"configs": {"myconfig": {"file": "./config.yml"}}}
}

test_no_configs_passes if {
	count(configs.deny) == 0 with input as {"services": {"app": {"image": "x"}}}
}

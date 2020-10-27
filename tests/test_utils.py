'''Implements tests for the utils module'''

import utils

def test_validate_uuid():
	'''Tests utils.validate_uuid'''
	assert utils.validate_uuid('5a56260b-aa5c-4013-9217-a78f094432c3'), 'Failed to validate good ID'
	assert not utils.validate_uuid('5a56260b-c-4013-9217-a78f094432c3'), 'Failed to reject bad ID'


def test_split_address():
	'''Tests utils.split_address'''
	
	out = utils.split_address('5a56260b-aa5c-4013-9217-a78f094432c3/example.com')
	assert not out.error(), "split_address error on good address"
	assert out['wid'] == '5a56260b-aa5c-4013-9217-a78f094432c3', 'split_address returned bad wid'
	assert out['domain'] == 'example.com', 'split_address returned bad domain'

	assert utils.split_address('5a56260b-aa5c-4013-9217-a78f094432c3'), \
			'Failed to error on bad address #1'
	
	assert utils.split_address('example.com'), 'Failed to error on bad address #2'
	
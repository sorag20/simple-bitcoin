from transactions import Transaction
from transactions import TransactionInput
from transactions import TransactionOutput
from transactions import CoinbaseTransaction

def main():

	t1 = CoinbaseTransaction('Itsuki_pubkey')
	
	print(t1.to_dict())
	
	result = t1.is_enough_inputs()
	
	print(result)

	t2 = Transaction(
    	[TransactionInput(t1, 0)],
    	[TransactionOutput('Umika_pubkey', 10.0), TransactionOutput('Itsuki_pubkey', 20.0)]
	)
	
	print(t2.to_dict())
	result2 = t2.is_enough_inputs()
	print(result2)

if __name__ == '__main__':
    main()
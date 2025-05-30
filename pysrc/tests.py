import asyncio

async def fetch_data(delay,id):
    print("Fetchin...")
    await asyncio.sleep(delay)
    return 'Recieved: {"data":"somethin", "id":'+str(id)+'}'

async def main():
    print("Starting the main coroutine")
    task=fetch_data(3,1)
    result=await task
    task2=fetch_data(3,2)
    print(result)

    result2=await task2
    print(result2)
    print("endof main coroutine")
asyncio.run(main())

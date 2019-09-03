These should work:
`/delay 30 sec say 30 sec`
`/delay 1:00pm say "It's 1:00pm!"`
`/delay 3:30pm EDT say "It's 3:00pm EDT!"`

DelaySay should say it can't schedule in the past:
`/delay 2019-09-01 1pm say 2019-09-01 1pm`

DelaySay should say it can't schedule so soon:
`/delay 1 sec say 1 sec`

DelaySay should say it can't schedule so far:
`/delay 200 days say 200 days`

DelaySay should say it can't parse the time "bogus":
`/delay bogus say bogus`

DelaySay should say that message text must be provided:
`/delay 12pm say`

DelaySay should say it can't parse the command / find the time or message:
`/delay bogus`
#!/usr/bin/env python
from selenium import webdriver
from selenium.webdriver.support.select import Select
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException, NoSuchAttributeException, ElementNotVisibleException
from selenium.webdriver.support.ui import WebDriverWait # available since 2.4.0
import time
import datetime
from unittest import TestCase
from urlparse import urlparse
from uuid import uuid4

class SeleniumTest(object):
    SCHEME = 'https'
    HOST = 'staging.weddingrepublic.com'
    USERNAME = 'tecywiz121@hotmail.com'
    PASSWORD = 'tecy121'
    REGISTRY = 'testregistry'

    FB1_ID = '100002874912733'
    FB1_USER = 'tecywiz121@gmail.com'
    FB1_PASSWORD = 'tecy121'

    FB2_ID = '100003852226108'
    FB2_USER = 'hana+anna@weddingrepublic.com'
    FB2_PASSWORD = 'spicedtea564'

    @property
    def base(self):
        """The scheme and host combined into a url, without trailing slash"""
        return self.SCHEME + '://' + self.HOST

    def new_driver(self):
        try:
            self.driver.quit()
            del self.driver
        except AttributeError:
            pass
        self.driver = webdriver.Firefox()

    def setUp(self):
        self.new_driver()
        if getattr(self, 'login_required', False):
            self.get('/login')
            self.login()

        if hasattr(self, 'path'):
            self.get(self.path)

    def tearDown(self):
        self.driver.quit()
        del self.driver

    def assertPath(self, expected, msg=None):
        """Check that the current browser path matches the expected path"""
        self.assertEqual(self.base + expected, self.driver.current_url, msg)

    def assertNotLoggedIn(self):
        try:
            dashboard = self.driver.find_element_by_class_name('dashboardpanel')
        except NoSuchElementException:
            return
        self.fail('Still logged in')

    def assertLoggedIn(self, first_name, last_name):
        dashboard = self.driver.find_element_by_class_name('dashboardpanel')
        text = ''.join(x.text for x in dashboard.find_elements())
        self.assertIn(' '.join((first_name, last_name)), text, msg='Not logged in or name not in dashboard')

    def login(self):
        self.post('/login', {'email': self.USERNAME, 'password': self.PASSWORD})
        self.wait_until_redirect('/login')

    def get(self, path):
        """Loads a web page in the current browser session relative to the base
        url.

        Also injects some testing javascript into the page to facilitate link
        checking."""
        self.driver.get(self.base + path)

        try:
            # Insert test javascript functions
            self.driver.execute_script('''
    (function(global) {
        var fetchResults = {};
        var fetchProcessing = {};
        var fetchStatus = function (address) {
            var client = new XMLHttpRequest();
            client.onreadystatechange = function () {
                if (this.readyState === 4) {
                    fetchResults[address] = this.status;
                    delete fetchProcessing[address];
                    log('deleting ' + address + ' ' + this.status);
                }
            };
            fetchProcessing[address] = true;
            log('adding ' + address);
            fetchResults[address] = 0;
            client.open("HEAD", address);
            client.send();
        };

        var getFetchResults = function () {
            return fetchResults;
        };

        var isFetchDone = function () {
            log(Object.keys(fetchProcessing).length);
            return Object.keys(fetchProcessing).length === 0;
        };

        var log = function (msg) {
            return;
            var body = document.getElementsByTagName('body') [0];
            var div = document.createElement('div');
            var text = document.createTextNode(msg);
            div.appendChild(text);
            body.appendChild(div);
        };

        var post = function (url, data) {
            var form = document.createElement('form'),
                body = document.getElementsByTagName('body') [0],
                element;
            form.action = url;
            form.method = "POST";

            for (var x in data) {
                element = document.createElement('input');
                element.type = 'hidden';
                element.name = x;
                element.value = data[x];
                form.appendChild(element);
            }

            body.appendChild(form);
            form.submit();
        };

        var extError = [];
        var extProcessing = {};

        var checkImages = function () {
            var targets = Array.prototype.slice.call(document.images);
            var body = body = document.getElementsByTagName('body') [0];

            for (var ii = 0; ii < targets.length; ii += 1) {
                var target = targets[ii];
                if (typeof (target.src) !== 'undefined' && target.src != '') {
                    log('watching: ' + target.src);
                    var src = target.src.toString();
                    var tester = document.createElement(target.tagName);

                    tester.onerror = function(error) {
                        var elem = error.target;
                        delete elem.onerror;
                        delete elem.onload;
                        extError.push(elem.src);
                        log('Error: ' + elem.src);
                        delete extProcessing[elem.src];
                        elem.parentNode.removeChild(elem);
                    };
                    tester.onload = function(error) {
                        var elem = error.target;
                        delete elem.onerror;
                        delete elem.onload;
                        log('Success: ' + elem.src);
                        delete extProcessing[elem.src];
                        elem.parentNode.removeChild(elem);
                    };
                    extProcessing[target.src] = true;
                    body.appendChild(tester);
                    tester.src = target.src;
                }
            }
        };

        var isImageCheckDone = function () {
            log(Object.keys(extProcessing).length);
            return Object.keys(extProcessing).length === 0;
        };

        var getImageCheckResults = function () {
            return extError;
        };

        global._test = {};
        global._test.fetchStatus = fetchStatus;
        global._test.getFetchResults = getFetchResults;
        global._test.isFetchDone = isFetchDone;
        global._test.post = post;
        global._test.checkImages = checkImages;
        global._test.isImageCheckDone = isImageCheckDone;
        global._test.getImageCheckResults = getImageCheckResults;
    }(window));
            ''');
        except WebDriverException:
            pass # Happens during a fast redirect, means test_missing won't work

    def fetch_status(self, url):
        """Executes the fetchStatus javascript test method. Adds a url to be
        tested."""
        self.driver.execute_script('window._test.fetchStatus("{}");'.format(url))

    def get_fetch_results(self):
        """Executes the getFetchResults javascript test method. Returns the
        current test results."""
        return self.driver.execute_script('return window._test.getFetchResults();')

    def is_fetch_done(self):
        """Executes the isFetchDone javascript test method. Returns the status
        of the current fetch."""
        return self.driver.execute_script('return window._test.isFetchDone();')

    def fetch_results(self):
        """Waits until the current fetch is complete, then checks the fetch
        results for errors."""
        try:
            WebDriverWait(self.driver, 30).until(lambda driver: self.is_fetch_done())
        except TimeoutException:
            pass
        results = self.get_fetch_results()
        results = filter(lambda (adr,sts): sts >= 400 or sts == 0, results.iteritems())
        errmsg = '\n\t'.join("{0} ({1})".format(x[0], x[1]) for x in results)
        self.assertTrue(len(results) == 0, msg="unable to load pages:\n\t{0}".format(errmsg))

    def _fetch_attr(self, attr):
        """Gets all elements in the browser with the specified attribute and
        executes fetch_status on them."""
        links = self.driver.find_elements_by_css_selector('*[{0}]'.format(attr))
        links = (x.get_attribute(attr) for x in links)

        # Remove urls that shouldn't be tested
        targets = set(x for x in links if x and urlparse(x).hostname and self.HOST in urlparse(x).hostname)
        ignore = set(self.base + x for x in ('/users/connect/facebook', '/blog'))
        targets -= ignore
        for target in targets:
            self.fetch_status(target)

    def fetch_links(self):
        """Gets all elements with an href tag and executes fetch_status on them"""
        self._fetch_attr('href')

    def fetch_external(self):
        """Gets all elements with an src tag and executes fetch_status on them"""
        self._fetch_attr('src')

    def images_check(self):
        """Executes the checkImages javascript test method"""
        incomplete = self.driver.execute_script('return window._test.checkImages();')

    def is_image_check_done(self):
        """Executes the isImageCheckDone javascript test method. Returns the status
        of the current image check."""
        return self.driver.execute_script('return window._test.isImageCheckDone();')

    def get_image_check_results(self):
        """Executes the getImageCheckResults javascript test method. Returns the
        current test results."""
        return self.driver.execute_script('return window._test.getImageCheckResults();')

    def images_results(self):
        """Waits until the current image check is complete, then checks the
        results for errors."""
        try:
            WebDriverWait(self.driver, 30).until(lambda driver: self.is_image_check_done())
        except TimeoutException:
            pass
        results = self.get_image_check_results()
        errmsg = '\n\t'.join(str(x) for x in results)
        self.assertTrue(len(results) == 0, msg="unable to load images:\n\t{0}".format(errmsg))

    def test_missing(self):
        if hasattr(self, 'path'):
            self.fetch_links()
            self.fetch_external()
            self.fetch_results()

            self.images_check()
            self.images_results()

    def wait_until_redirect(self, src):
        """Waits for the current absolute path to change from `src` to something
        else."""
        try:
            WebDriverWait(self.driver, 5).until(lambda x: not urlparse(x.current_url).path.endswith(src))
        except TimeoutException:
            self.fail('timeout waiting for redirect from ' + src)

    def post(self, url, data={}):
        """Executes the post javascript test method. Injects a form into the
        current page and POSTs it to the specified url."""
        post_data = []
        for k, v in data.iteritems():
            k = k.replace("'", "\\'").replace('\n', '\\n')
            v = v.replace("'", "\\'").replace('\n', '\\n')
            post_data.append("'{0}': '{1}'".format(k,v))
        post_data = '{' + ', '.join(post_data) + '}'
        self.driver.execute_script('window._test.post("{0}", {1});'.format(url, post_data))

    def create_email(self):
        """Returns a relatively unique email address"""
        # return 'test+{0}@example.com'.format(uuid4())
        return 'test+{0}@example.com'.format(int(time.time() * 10))

    def interact(self, actions):
        """Execute a series of actions in the browser.

        `actions` is an iterable containing pairs of a css selector and an action
            to run on matched elements.  Actions can be callables (which will
            be passed a single element) or strings (which will be typed in the
            matched element)
        """
        for item, action in actions:
            elements = self.driver.find_elements_by_css_selector(item)
            if callable(action):
                for elem in elements:
                    action(elem)
            elif isinstance(action, basestring):
                for elem in elements:
                    elem.send_keys(action)
            else:
                raise Exception('unknown action')

class TestIndex(SeleniumTest, TestCase):
    path = '/'

class TestLogin(SeleniumTest, TestCase):
    path = '/login'

class TestRegister(SeleniumTest, TestCase):
    path = '/register'

    def test_register_and_login(self):
        # Test data
        test_email = self.create_email()
        test_password = 'password'

        # Get registration form elements
        first_name = self.driver.find_element_by_name('first_name')
        last_name = self.driver.find_element_by_name('last_name')
        email = self.driver.find_element_by_name('email')
        password = self.driver.find_element_by_name('password')

        # Populate form
        first_name.send_keys('John')
        last_name.send_keys('Doe')
        email.send_keys(test_email)
        password.send_keys(test_password)

        # Submit form
        first_name.submit()

        self.wait_until_redirect('/register')

        # Check that we're logged in
        self.assertLoggedIn('John', 'Doe')

        self.get('/logout')
        self.wait_until_redirect('/logout')
        time.sleep(2)
        self.get('/login')

        # Get login form elements
        email = self.driver.find_element_by_name('email')
        password = self.driver.find_element_by_name('password')

        # Populate login form
        email.send_keys(test_email)
        password.send_keys(test_password)

        # Submit the login form
        password.submit()

        self.wait_until_redirect('/login')

        self.assertLoggedIn('John', 'Doe')

    def test_register_facebook(self):
        self.get('/users/connect/facebook')
        self.wait_until_redirect('/users/connect/facebook')

        email = self.driver.find_element_by_name('email')
        password = self.driver.find_element_by_name('pass')

        email.send_keys(self.FB1_USER)
        password.send_keys(self.FB1_PASSWORD)

        password.submit()

        self.wait_until_redirect('/login.php') # Facebook's login page

        # Permissions page
        try:
            go_to_app = self.driver.find_element_by_name('grant_required_clicked')
            go_to_app.click()
            self.wait_until_redirect('/dialog/oauth')

            allow = self.driver.find_element_by_name('grant_clicked')
            allow.click()
            self.wait_until_redirect('/dialog/permissions.request')
        except NoSuchElementException:
            pass # Application was already added to FB

        try:
            email = self.driver.find_element_by_name('email')
        except NoSuchElementException:
            # If the facebook user is already linked, the site logs in as them instead of creating a new user
            self.assertLoggedIn('Tristali', 'Jones')
            self.skipTest('facebook user already linked')
            return
        email.clear()
        email.send_keys(self.create_email())

        submit = self.driver.find_element_by_css_selector("input[type='submit']")
        submit.click()

        self.wait_until_redirect('/users/connect/facebook')

        self.assertLoggedIn('Tristali', 'Jones')

class TestSample(SeleniumTest, TestCase):
    path = '/sample'

class TestCreate(SeleniumTest, TestCase):
    path = '/create'
    login_required = True

    def test_gender_select(self):
        buttons = self.driver.find_elements_by_css_selector('.genderSelector')

        for btn in buttons:
            name = btn.get_attribute('id')[:-len('GenderSelector')]
            maleRadio = self.driver.find_element_by_id(name + 'Male')
            femaleRadio = self.driver.find_element_by_id(name + 'Female')
            for x in range(2):
                # Click the button
                male_1 = 'male' in btn.get_attribute('class')
                btn.click()
                male_2 = 'male' in btn.get_attribute('class')

                # Make sure the class switched
                self.assertNotEqual(male_1, male_2, msg='Gender selector not switching')

                # Make sure the associated radio buttons were flipped
                selected = maleRadio if male_2 else femaleRadio
                unselected = maleRadio if not male_2 else femaleRadio

                self.assertTrue(selected.is_selected(), msg='Radio button for selected gender not checked')
                self.assertFalse(unselected.is_selected(), msg='Radio button for incorrect gender checked')

    def test_date_popup(self):
        has_datepicker = self.driver.find_elements_by_css_selector('.hasDatepicker')
        body = self.driver.find_element_by_tag_name('body')

        for field in has_datepicker:
            body.click()
            field.click()
            try:
                WebDriverWait(self.driver, 5).until(lambda x: x.find_element_by_id('ui-datepicker-div').value_of_css_property('display') <> 'none')
            except TimeoutException:
                self.fail('Datepicker took too long to appear')

    def _create_registry(self, url_code, today=datetime.date.today()):
        self.interact([
            ('#wp_1_first_name', 'First1'),
            ('#wp_1_last_name', 'Last1'),
            ('#wp_2_first_name', 'First2'),
            ('#wp_2_last_name', 'Last2'),
            ('#firstPersonGenderSelector', WebElement.click),
            ('#secondPersonGenderSelector', WebElement.click),
            ('#url_code', WebElement.click),
            ('#url_code', lambda x: self.assertTrue(x.get_attribute('value'), msg="url_code did not get populated")),
            ('#url_code', WebElement.clear),
            ('#url_code', url_code),
            ('#wedding_date', today.strftime('%Y-%m-%d')),
            ('#close_date', (today + datetime.timedelta(days=1)).strftime('%Y-%m-%d')),
            ("*[type='submit']", WebElement.click),
        ])

    def test_create_registry(self):
        url_code = str(uuid4()).replace('-', '')
        self._create_registry(url_code)
        self.wait_until_redirect('/create')
        self.assertPath('/registry/customize/' + url_code)

    def test_reserved_url(self):
        self._create_registry('about')
        WebDriverWait(self.driver, 10).until(lambda x: x.find_element_by_css_selector('.errormsg'))
        errors = self.driver.find_elements_by_css_selector('.errormsg')
        self.assertTrue(any('custom url is not allowed' in error.text.lower() for error in errors))

    def test_invalid_url(self):
        self._create_registry('^%$$$#$#')
        WebDriverWait(self.driver, 10).until(lambda x: x.find_element_by_css_selector('.errormsg'))
        errors = self.driver.find_elements_by_css_selector('.errormsg')
        self.assertTrue(any('alpha-numeric' in error.text.lower() for error in errors))

class TestGifts(SeleniumTest, TestCase):
    path = '/registry/mygifts/{0}/'.format(SeleniumTest.REGISTRY)
    login_required = True

    def _open_gift_dialog(self, gift_id=1):
        self.interact([('li[data-item-id="{}"]'.format(gift_id), WebElement.click)])
        time.sleep(1) # TODO: Replace with a WebDriverWait

    def test_add_remove_piece(self):
        self._open_gift_dialog()
        add_pieces = self.driver.find_element_by_id('addPieces')
        reduce_pieces = self.driver.find_element_by_id('reducePieces')
        item_pieces = Select(self.driver.find_element_by_name('qty'))

        c = 1
        f = 0
        while c < 30:
            try:
                add_pieces.click()
                c += 1
                self.assertEqual(item_pieces.first_selected_option.get_attribute('value'), str(c), msg="Number of pieces not synchronized (add)")
            except ElementNotVisibleException:
                f += 1
                self.assertTrue(f < 10, msg="Could not click to add pieces")

        f = 0
        while c > 1:
            try:
                reduce_pieces.click()
                c -= 1
                self.assertEqual(item_pieces.first_selected_option.get_attribute('value'), str(c), msg="Number of pieces not synchronized (reduce)")
            except ElementNotVisibleException:
                f += 1
                self.assertTrue(f < 10, msg="Could not click to reduce pieces")

    def test_add_gift(self):
        before_add = self.driver.find_elements_by_css_selector('ul#wishlist li')
        self._open_gift_dialog()
        self.interact([('#addExistingItemForm *[type="submit"]', WebElement.click)])

        try:
            WebDriverWait(self.driver, 5).until(lambda x: len(x.find_elements_by_css_selector('ul#wishlist li')) > len(before_add))
        except TimeoutException:
            self.fail('Item not added to wishlist')

class TestInvite(SeleniumTest, TestCase):
    path = '/registry/guestlist/{0}/'.format(SeleniumTest.REGISTRY)
    login_required = True

    def test_facebook_invite(self):
        main_window = self.driver.window_handles[0]

        self.interact([
            ('a[href="#invite"]', WebElement.click),
            ('#facebook-invite', WebElement.click),
        ])

        try:
            WebDriverWait(self.driver, 10).until(lambda x: len(x.window_handles) > 1)
        except TimeoutException:
            self.fail('Timeout waiting for Facebook popup')
        popup = filter(lambda x: x <> main_window, self.driver.window_handles)[0]
        self.driver.switch_to_window(popup)

        self.interact([
            ('#email', self.FB1_USER),
            ('#pass', self.FB1_PASSWORD),
            ('*[type="submit"]', WebElement.click)
        ])
        self.wait_until_redirect('/login.php')
        WebDriverWait(self.driver, 5).until(lambda x: x.find_element_by_css_selector('input[value="{}"]'.format(self.FB2_ID)))

        # XXX: For some reason this doesn't work with interact
        other_user = self.driver.find_element_by_css_selector('input[value="{}"]'.format(self.FB2_ID))
        other_user.click()

        self.interact([
            ('input[name="ok_clicked"]', WebElement.click),
        ])

        try:
            WebDriverWait(self.driver, 10).until(lambda x: len(x.window_handles) < 2)
        except TimeoutException:
            self.fail('Timeout waiting for Facebook popup to close')

        # Reset driver to log in as FB2
        self.new_driver()

        self.driver.get('https://www.facebook.com/login.php')

        self.interact([
            ('#email', self.FB2_USER),
            ('#pass', self.FB2_PASSWORD),
            ('#login_form input[type="submit"]', WebElement.click),
        ])

        self.wait_until_redirect('/login.php')

        # Hop over to notifications page
        self.driver.get('https://www.facebook.com/notifications')

        # Find most recent notification and click it
        def _find_notification(driver):
            notifications = driver.find_elements_by_css_selector('.notification')
            notifications.sort(lambda y,x: cmp(x.get_attribute('data-notiftime'), y.get_attribute('data-notiftime')))
            for notification in notifications:
                links = notification.find_elements_by_tag_name('a')
                links = [x for x in links if 'a request' in x.text or 'requests' in x.text]
                try:
                    return links[0]
                except IndexError:
                    pass
            return False

        WebDriverWait(self.driver, 30).until(_find_notification)
        link = _find_notification(self.driver)
        link.click()

        self.wait_until_redirect('/notifications')

        WebDriverWait(self.driver, 5).until(lambda x: x.find_element_by_name('iframe_canvas_fb_https'))
        self.driver.switch_to_frame(self.driver.find_element_by_name('iframe_canvas_fb_https'))
        html = self.driver.page_source
        self.assertNotIn('uh oh', html.lower())


if __name__ == '__main__':
    import unittest
    unittest.main()
